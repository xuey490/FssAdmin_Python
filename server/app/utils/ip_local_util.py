import ipaddress

import httpx
from starlette.requests import Request

from app.config.setting import settings
from app.core.logger import logger

# 归属地缓存：IP 几乎不变化，缓存 7 天可显著减少外网请求
_IP_CACHE_TTL = 7 * 24 * 3600
# 硬超时（秒），避免外网查询阻塞主流程
_IP_QUERY_TIMEOUT = 3.0


def get_client_ip(request: Request) -> str | None:
    """从请求中解析客户端真实 IP。优先取 X-Forwarded-For 第一个，回退到 ``request.client.host``。

    返回 None 表示客户端不存在（如 UNIX socket 场景）。
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


class IpLocalUtil:
    """获取 IP 归属地工具类（带 Redis 缓存、硬超时、降级）。"""

    @classmethod
    def is_valid_ip(cls, ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @classmethod
    def is_private_ip(cls, ip: str) -> bool:
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return False

    @classmethod
    async def resolve_location_for_log(cls, redis, ip: str | None) -> str | None:
        """登录日志写入入口：仅返回可同步获取的值（内网/缓存/降级），

        外网查询由后台任务异步执行（见 ``resolve_location_async``）。
        """
        if not ip:
            return None
        if not settings.IP_LOCATION_ENABLE:
            return "内网IP" if cls.is_private_ip(ip) else "未解析(已关闭归属地查询)"
        if cls.is_private_ip(ip):
            return "内网IP"
        if redis:
            cached = await cls._cache_get(redis, ip)
            if cached is not None:
                return cached
        return "归属地查询中"

    @classmethod
    async def resolve_location_async(cls, redis, ip: str) -> str:
        """异步查询归属地（含缓存、降级、硬超时）。"""
        if not cls.is_valid_ip(ip):
            return "未知"
        if cls.is_private_ip(ip):
            return "内网IP"

        cached = await cls._cache_get(redis, ip) if redis else None
        if cached is not None:
            return cached

        result = await cls._query_with_timeout(ip)
        if redis:
            await cls._cache_set(redis, ip, result)
        return result

    @classmethod
    async def _query_with_timeout(cls, ip: str) -> str:
        """在硬超时内尝试主备两个 API，全部失败返回未知。"""
        apis = [
            ("https://ip9.com.cn/get", cls._parse_ip9),
            ("http://ip-api.com/json", cls._parse_ipapi),
        ]
        for url, parser in apis:
            try:
                async with httpx.AsyncClient(timeout=_IP_QUERY_TIMEOUT) as client:
                    resp = await client.get(
                        url if "ip-api" in url else f"{url}?ip={ip}",
                        params={} if "ip-api" in url else None,
                    )
                    if resp.status_code == 200:
                        location = parser(resp.json())
                        if location:
                            return location
            except Exception as e:
                logger.warning(f"IP 归属地 API 失败: {url} - {e}")
        return "未知"

    @staticmethod
    def _parse_ip9(data: dict) -> str | None:
        if data.get("ret") != 200:
            return None
        d = data.get("data") or {}
        parts = [d.get("country"), d.get("prov"), d.get("city"), d.get("area"), d.get("isp")]
        joined = "-".join(filter(None, parts))
        return joined or None

    @staticmethod
    def _parse_ipapi(data: dict) -> str | None:
        if data.get("status") != "success":
            return None
        parts = [data.get("country"), data.get("regionName"), data.get("city"), data.get("isp")]
        joined = "-".join(filter(None, parts))
        return joined or None

    @staticmethod
    async def _cache_get(redis, ip: str) -> str | None:
        try:
            from app.core.redis_crud import RedisCURD
            value = await RedisCURD(redis).get(f"ip:location:{ip}")
            if value is None:
                return None
            return value.decode("utf-8") if isinstance(value, bytes) else str(value)
        except Exception:
            return None

    @staticmethod
    async def _cache_set(redis, ip: str, value: str) -> None:
        try:
            from app.core.redis_crud import RedisCURD
            await RedisCURD(redis).set(f"ip:location:{ip}", value, expire=_IP_CACHE_TTL)
        except Exception:
            pass
