"""Monitor / core server 路由，对齐 web + phpserver。"""

from __future__ import annotations

import asyncio
import gc
import platform
import sys
import threading
import time
import tracemalloc
from datetime import datetime, timedelta
from typing import Any

import psutil
from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis

from app.common.response import SuccessResponse
from app.config.path_conf import BASE_DIR
from app.config.setting import settings
from app.core.dependencies import AuthPermission, get_current_user, redis_getter
from app.core.base_schema import AuthSchema
from app.core.logger import logger
from app.utils.common_util import bytes2human

CoreServerRouter = APIRouter(tags=["核心监控"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


def _binary_preview(raw: bytes, *, limit: int = 64) -> dict[str, Any]:
    """不可 UTF-8 解码的 Redis 值（如 apscheduler pickle）展示用。"""
    return {
        "_binary": True,
        "size": len(raw),
        "preview_hex": raw[:limit].hex(),
        "note": "binary/non-utf8 value",
    }


def _format_redis_scalar(val: Any) -> Any:
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except UnicodeDecodeError:
            return _binary_preview(val)
    return val


async def _redis_raw_command(redis: Redis, *args: Any) -> Any:
    """绕过 decode_responses，读原始 bytes（应对 pickle 等二进制 key）。"""
    conn = await redis.connection_pool.get_connection("_")
    try:
        await conn.send_command(*args)
        return await conn.read_response(disable_decoding=True)
    finally:
        await redis.connection_pool.release(conn)


async def _redis_get_safe(redis: Redis, key: str) -> Any:
    try:
        return await redis.get(key)
    except UnicodeError:
        raw = await _redis_raw_command(redis, "GET", key)
        return _format_redis_scalar(raw)


async def _redis_hgetall_safe(redis: Redis, key: str) -> Any:
    try:
        return await redis.hgetall(key)
    except UnicodeError:
        raw = await _redis_raw_command(redis, "HGETALL", key)
        if not raw:
            return {}
        # HGETALL 扁平 [k,v,k,v,...]
        out: dict[str, Any] = {}
        it = iter(raw if isinstance(raw, (list, tuple)) else [])
        for k in it:
            v = next(it, None)
            out[str(_format_redis_scalar(k))] = _format_redis_scalar(v)
        return out


async def _redis_list_safe(redis: Redis, key: str, start: int = 0, end: int = 50) -> Any:
    try:
        return await redis.lrange(key, start, end)
    except UnicodeError:
        raw = await _redis_raw_command(redis, "LRANGE", key, start, end)
        return [_format_redis_scalar(x) for x in (raw or [])]


async def _redis_smembers_safe(redis: Redis, key: str) -> Any:
    try:
        return list(await redis.smembers(key))
    except UnicodeError:
        raw = await _redis_raw_command(redis, "SMEMBERS", key)
        return [_format_redis_scalar(x) for x in (raw or [])]


async def _redis_zrange_safe(redis: Redis, key: str, start: int = 0, end: int = 50) -> Any:
    try:
        return await redis.zrange(key, start, end, withscores=True)
    except UnicodeError:
        raw = await _redis_raw_command(redis, "ZRANGE", key, start, end, "WITHSCORES")
        if not raw:
            return []
        out = []
        it = iter(raw)
        for member in it:
            score = next(it, 0)
            try:
                score_f = float(score)
            except (TypeError, ValueError):
                score_f = score
            out.append((_format_redis_scalar(member), score_f))
        return out


def _fmt_uptime(seconds: float | int) -> str:
    return str(timedelta(seconds=int(seconds)))


def _cpu_model() -> str:
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/cpuinfo", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        if sys.platform == "win32":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if name:
                return str(name).strip()
        name = platform.processor() or ""
        if name:
            return name
    except Exception:
        pass
    return ""


# ponytail: cpu_percent(interval=N) 会阻塞事件循环；interval=None 读上次采样。模块导入时打一次底。
psutil.cpu_percent(interval=None)

_REMOTE_FS = frozenset({"nfs", "nfs4", "cifs", "smb", "smbfs", "fuse.sshfs"})
_STATIC_ENV: dict[str, Any] | None = None
_MONITOR_CACHE: tuple[float, dict[str, Any]] | None = None
_MONITOR_CACHE_TTL = 3.0
_MEMORY_PREVIOUS_SNAPSHOT: tracemalloc.Snapshot | None = None
_MEMORY_PREVIOUS_RSS: int | None = None

if settings.MEMORY_DIAGNOSTICS_ENABLE:
    # ponytail: 仅开发期保留 10 帧；每次监控请求只留上一份快照，避免诊断工具本身积累快照。
    tracemalloc.start(10)


def _is_local_fixed_partition(part: Any) -> bool:
    """跳过光驱 / 网络盘 / 可移动盘。Windows 上对这些盘做 disk_usage 经常卡 10s+。"""
    fstype = (getattr(part, "fstype", None) or "").strip().lower()
    if not fstype or fstype in _REMOTE_FS:
        return False
    opts = (getattr(part, "opts", None) or "").lower()
    if any(tag in opts for tag in ("cdrom", "remote", "removable")):
        return False
    device = (getattr(part, "device", None) or "").replace("/", "\\")
    if device.startswith("\\\\"):
        return False
    if sys.platform == "win32":
        return "fixed" in opts
    return True


def _win_fixed_mounts() -> list[str]:
    """Windows 下列本地固定盘。不用 psutil.disk_partitions：GetVolumeInformation 会把休眠盘拖到 10s+。"""
    import ctypes
    import os

    get_type = ctypes.windll.kernel32.GetDriveTypeW
    get_type.argtypes = [ctypes.c_wchar_p]
    get_type.restype = ctypes.c_uint
    drive_fixed = 3
    return [d for d in os.listdrives() if get_type(d) == drive_fixed]


def _load_average() -> str:
    if sys.platform == "win32":
        try:
            return f"{psutil.cpu_percent(interval=None):.2f}"
        except Exception:
            return "0.00"
    try:
        if hasattr(psutil, "getloadavg"):
            return f"{psutil.getloadavg()[0]:.2f}"
    except (AttributeError, OSError):
        pass
    try:
        return f"{psutil.cpu_percent(interval=None):.2f}"
    except Exception:
        return "0.00"


def _memory(mem: Any | None = None) -> dict[str, Any]:
    mem = mem or psutil.virtual_memory()
    proc = psutil.Process().memory_info()
    return {
        "total": bytes2human(mem.total),
        "used": bytes2human(mem.used),
        "free": bytes2human(mem.free),
        "php": bytes2human(proc.rss),
        "rate": f"{round(mem.percent, 1)}%",
    }


def _static_env() -> dict[str, Any]:
    global _STATIC_ENV
    if _STATIC_ENV is not None:
        return _STATIC_ENV
    env = getattr(settings, "ENVIRONMENT", None)
    env_name = getattr(env, "value", None) or env or "dev"
    try:
        import fastapi

        fastapi_ver = getattr(fastapi, "__version__", "")
    except Exception:
        fastapi_ver = ""
    _STATIC_ENV = {
        "php_version": platform.python_version(),
        "nestjs_version": "FastAdmin",
        "os": f"{platform.system()} {platform.release()}",
        "hostname": platform.node(),
        "cpu_model": _cpu_model(),
        "cpu_cores": psutil.cpu_count(logical=True) or 1,
        "arch": platform.machine() or platform.architecture()[0],
        "project_path": str(BASE_DIR.resolve()),
        "error_reporting": str(env_name),
        "loaded_extensions": f"Python {sys.version.split()[0]} / FastAPI {fastapi_ver}".strip(),
    }
    return _STATIC_ENV


def _php_env(mem: Any | None = None) -> dict[str, Any]:
    """字段名保持 phpEnv.*（web 兼容），内容为 Python/FastAdmin 运行环境。"""
    now = datetime.now()
    boot = datetime.fromtimestamp(psutil.boot_time())
    proc = psutil.Process()
    proc_start = datetime.fromtimestamp(proc.create_time())
    mem = mem or psutil.virtual_memory()
    return {
        **_static_env(),
        "load_average": _load_average(),
        "uptime": _fmt_uptime((now - boot).total_seconds()),
        "process_uptime": _fmt_uptime((now - proc_start).total_seconds()),
        "memory_limit": bytes2human(mem.total),
    }


def _disk() -> list[dict[str, Any]]:
    disks: list[dict[str, Any]] = []
    if sys.platform == "win32":
        specs = [(mp, mp) for mp in _win_fixed_mounts()]
    else:
        specs = [
            (part.device, part.mountpoint)
            for part in psutil.disk_partitions(all=False)
            if _is_local_fixed_partition(part)
        ]
    for device, mount in specs:
        try:
            usage = psutil.disk_usage(mount)
        except Exception:
            continue
        disks.append(
            {
                "filesystem": device,
                "size": bytes2human(usage.total),
                "used": bytes2human(usage.used),
                "available": bytes2human(usage.free),
                "use_percentage": f"{usage.percent}%",
                "mounted_on": mount,
            }
        )
    return disks


def _collect_monitor() -> dict[str, Any]:
    mem = psutil.virtual_memory()
    return {"memory": _memory(mem), "phpEnv": _php_env(mem), "disk": _disk()}


def _memory_diagnostics() -> dict[str, Any]:
    """返回并记录相邻两次监控请求之间仍存活的 Python 分配差异。"""
    global _MEMORY_PREVIOUS_SNAPSHOT, _MEMORY_PREVIOUS_RSS
    if not settings.MEMORY_DIAGNOSTICS_ENABLE:
        return {}

    proc = psutil.Process()
    rss = proc.memory_info().rss
    try:
        uss = int(proc.memory_full_info().uss)
    except (AttributeError, psutil.Error):
        uss = None

    current, peak = tracemalloc.get_traced_memory()
    snapshot = tracemalloc.take_snapshot()
    previous = _MEMORY_PREVIOUS_SNAPSHOT
    top: list[dict[str, Any]] = []
    if previous is not None:
        for stat in snapshot.compare_to(previous, "lineno")[:8]:
            if stat.size_diff <= 0:
                continue
            frame = stat.traceback[0]
            top.append(
                {
                    "location": f"{frame.filename}:{frame.lineno}",
                    "size_diff": stat.size_diff,
                    "count_diff": stat.count_diff,
                }
            )

    rss_delta = None if _MEMORY_PREVIOUS_RSS is None else rss - _MEMORY_PREVIOUS_RSS
    _MEMORY_PREVIOUS_SNAPSHOT = snapshot
    _MEMORY_PREVIOUS_RSS = rss
    result = {
        "rss": rss,
        "rss_delta": rss_delta,
        "uss": uss,
        "python_traced": current,
        "python_peak": peak,
        "gc_counts": gc.get_count(),
        "threads": threading.active_count(),
        "top_growth": top,
    }
    logger.warning(
        "MEMDIAG rss={}({:+}) uss={} traced={} peak={} threads={} top={}",
        bytes2human(rss),
        rss_delta or 0,
        bytes2human(uss) if uss is not None else "-",
        bytes2human(current),
        bytes2human(peak),
        result["threads"],
        [
            f"{item['location']} +{bytes2human(item['size_diff'])} ({item['count_diff']:+})"
            for item in top[:3]
        ],
    )
    return result


@CoreServerRouter.get("/core/server/monitor")
async def server_monitor(auth: AuthSchema = Depends(get_current_user), diagnostics: bool = False):
    global _MONITOR_CACHE
    now = time.monotonic()
    cached = _MONITOR_CACHE
    # ponytail: tracemalloc.compare_to 在分配量较大时可耗时数秒；普通监控绝不能触发它。
    debug = _memory_diagnostics() if diagnostics else {}
    if cached and now - cached[0] < _MONITOR_CACHE_TTL:
        return _ok({**cached[1], "memoryDebug": debug})
    data = await asyncio.to_thread(_collect_monitor)
    _MONITOR_CACHE = (now, data)
    return _ok({**data, "memoryDebug": debug})


@CoreServerRouter.get("/core/server/cache")
async def server_cache(redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    info = await redis.info("memory")
    stats = await redis.info("stats")
    hits = int(stats.get("keyspace_hits") or 0)
    misses = int(stats.get("keyspace_misses") or 0)
    total = hits + misses
    hit_rate = f"{round(hits * 100 / total, 2)}%" if total else "0%"
    return _ok(
        {
            "opcache": {
                "enabled": True,
                "memory_used": info.get("used_memory_human") or "-",
                "memory_free": "-",
                "memory_total": info.get("maxmemory_human") or "-",
                "hit_rate": hit_rate,
                "cached_scripts": 0,
                "max_files": 0,
            },
            "php_version": platform.python_version(),
            "enabled": True,
            "memory_used": info.get("used_memory_human") or "-",
            "hit_rate": hit_rate,
        }
    )


@CoreServerRouter.post("/core/server/clear")
@CoreServerRouter.delete("/core/server/cache")
async def clear_cache(redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    # ponytail: 不清 FLUSHALL；只清常见应用前缀，避免误伤整库
    prefixes = ("fastapi-admin:", "cache:", "config:", "dict:", "captcha:", "refresh:token:")
    deleted = 0
    for prefix in prefixes:
        keys = await _scan_keys(redis, f"{prefix}*")
        if keys:
            deleted += int(await redis.delete(*keys))
    return _ok({"cleared": {"redis_prefix": True, "deleted": deleted}, "message": "缓存已清理", "success": True})


@CoreServerRouter.get("/core/server/redis")
async def redis_info(redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    info = await redis.info()
    return _ok(
        {
            "variable": info,
            "uptime_in_seconds": info.get("uptime_in_seconds"),
            "uptime_in_days": info.get("uptime_in_days"),
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human") or info.get("used_memory"),
        }
    )


async def _scan_keys(redis: Redis, pattern: str, count: int = 200) -> list[str]:
    keys: list[str] = []
    cursor = 0
    while True:
        cursor, batch = await redis.scan(cursor=cursor, match=pattern, count=count)
        keys.extend(batch)
        if cursor == 0 or len(keys) >= 500:
            break
    return keys[:500]


@CoreServerRouter.get("/core/server/redis/browser/level1")
async def redis_level1(pattern: str = "*", redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    keys = await _scan_keys(redis, pattern)
    groups: dict[str, int] = {}
    for k in keys:
        prefix = k.split(":")[0] if ":" in k else k
        groups[prefix] = groups.get(prefix, 0) + 1
    return _ok([{"key": k, "count": c} for k, c in sorted(groups.items())])


@CoreServerRouter.get("/core/server/redis/browser/level2")
async def redis_level2(prefix: str = "", redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    keys = await _scan_keys(redis, f"{prefix}*")
    out = []
    for k in keys[:100]:
        ttl = await redis.ttl(k)
        t = await redis.type(k)
        out.append({"key": k, "type": t, "fullKey": k, "ttl": ttl})
    return _ok(out)


@CoreServerRouter.get("/core/server/redis/browser/level3")
async def redis_level3(prefix: str = "", redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    keys = await _scan_keys(redis, f"{prefix}*")
    out = []
    for k in keys[:100]:
        ttl = await redis.ttl(k)
        out.append({"key": k, "ttl": ttl, "size": 0})
    return _ok(out)


@CoreServerRouter.get("/core/server/redis/browser/key-info")
async def redis_key_info(key: str, redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    t = await redis.type(key)
    ttl = await redis.ttl(key)
    value: Any = None
    if t == "string":
        value = await _redis_get_safe(redis, key)
    elif t == "hash":
        value = await _redis_hgetall_safe(redis, key)
    elif t == "list":
        value = await _redis_list_safe(redis, key)
    elif t == "set":
        value = await _redis_smembers_safe(redis, key)
    elif t == "zset":
        value = await _redis_zrange_safe(redis, key)
    return _ok({"key": key, "type": t, "ttl": ttl, "size": 0, "value": value})


@CoreServerRouter.delete("/core/server/redis/browser/delete")
async def redis_delete(request: Request, redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    deleted = 0
    if body.get("key"):
        deleted = await redis.delete(body["key"])
    elif body.get("pattern"):
        keys = await _scan_keys(redis, body["pattern"])
        if keys:
            deleted = await redis.delete(*keys)
    return _ok({"deleted": deleted})


@CoreServerRouter.get("/core/redis/info")
async def core_redis_info(redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    return await redis_info(redis, auth)


@CoreServerRouter.get("/core/redis/operations")
async def core_redis_operations(redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    # ponytail: Redis 无实时命令流；返回 commandstats 摘要供前端展示
    try:
        stats = await redis.info("commandstats")
        out = []
        for k, v in stats.items():
            name = k.replace("cmdstat_", "") if isinstance(k, str) else str(k)
            if isinstance(v, dict):
                out.append({"command": name, "calls": v.get("calls"), "usec": v.get("usec")})
            else:
                out.append({"command": name, "raw": v})
        return _ok(out)
    except Exception:
        return _ok([])


@CoreServerRouter.get("/core/redis/keys")
async def core_redis_keys(pattern: str = "*", redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    return _ok(await _scan_keys(redis, pattern))


@CoreServerRouter.delete("/core/redis/deleteKeys")
async def core_redis_delete_keys(request: Request, redis: Redis = Depends(redis_getter), auth: AuthSchema = Depends(get_current_user)):
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    keys = body.get("keys") or []
    deleted = await redis.delete(*keys) if keys else 0
    return _ok({"deleted": deleted})

