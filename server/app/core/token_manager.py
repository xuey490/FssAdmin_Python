"""Token 管理器 — JWT / Redis 双模式（对齐第三方 TokenManager）。"""

from __future__ import annotations

import json
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import jwt
from redis.asyncio import Redis

from app.config.setting import settings
from app.core.base_schema import JWTPayloadSchema
from app.core.exceptions import CustomException
from app.core.logger import logger

SessionType = Literal["jwt", "redis-token"]

_VERSION_KEY = "token:version:{uid}"
_SESSION_KEY = "token:session:{sid}"
_USER_SESSIONS_KEY = "token:user_sessions:{uid}"
_ACCESS_KEY = "token:access:{token}"
_USER_INFO_KEY = "token:user_info:{token}"
_REFRESH_KEY = "token:refresh:{token}"
_USER_TOKENS_KEY = "token:user_tokens:{uid}"


@dataclass
class AuthTokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass
class TokenIssueContext:
    """签发令牌所需的用户上下文（由 AuthService 从 DB 组装）。"""

    uid: int
    username: str
    nickname: str
    tenant_id: int
    roles: list[str]
    is_super: bool = False
    access_ttl: int | None = None
    # 在线会话附加信息（可选，对齐 web online 表格）
    ipaddr: str | None = None
    login_type: str | None = None
    dept_name: str | None = None
    login_location: str | None = None
    os: str | None = None
    browser: str | None = None


class TokenManager(ABC):
    @abstractmethod
    async def generate_token(self, ctx: TokenIssueContext) -> AuthTokenPair: ...

    @abstractmethod
    async def parse_token(self, token: str) -> JWTPayloadSchema | None: ...

    @abstractmethod
    async def validate_token(self, token: str) -> bool: ...

    @abstractmethod
    async def resolve_refresh(self, refresh_token: str) -> int | None:
        """校验 refresh，返回 user_id；无效返回 None。Redis 模式会消费（删除）旧 refresh。"""
        ...

    @abstractmethod
    async def invalidate_token(self, token: str) -> None: ...

    @abstractmethod
    async def invalidate_user_sessions(self, user_id: int) -> None: ...

    @abstractmethod
    async def list_sessions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None: ...


def _access_ttl(ctx: TokenIssueContext) -> int:
    ttl = int(ctx.access_ttl or settings.ACCESS_TOKEN_EXPIRE_SECONDS or 3600)
    return ttl if ttl >= 60 else 3600


def _refresh_ttl() -> int:
    ttl = int(settings.REFRESH_TOKEN_EXPIRE_SECONDS or 43200)
    return ttl if ttl >= 60 else 43200


def _session_payload(ctx: TokenIssueContext, session_id: str) -> dict[str, Any]:
    login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 同时写 camelCase（web）与 snake_case（内部），避免列表映射丢失
    return {
        "tokenId": session_id,
        "session_id": session_id,
        "userName": ctx.username,
        "user_name": ctx.username,
        "name": ctx.nickname or ctx.username,
        "deptName": ctx.dept_name or "",
        "dept_name": ctx.dept_name or "",
        "user_id": ctx.uid,
        "tenant_id": ctx.tenant_id,
        "is_superuser": bool(ctx.is_super),
        "ipaddr": ctx.ipaddr or "",
        "loginLocation": ctx.login_location or "",
        "login_location": ctx.login_location or "",
        "os": ctx.os or "",
        "browser": ctx.browser or "",
        "loginTime": login_time,
        "login_time": login_time,
        "login_type": ctx.login_type or "PC端",
    }


# =====================================================================
# JWT 实现（access/refresh 均为 JWT；Redis 存 version + 会话索引）
# =====================================================================


class JwtTokenManager(TokenManager):
    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis
        self._secret = settings.SECRET_KEY
        self._alg = settings.ALGORITHM

    async def _get_token_version(self, user_id: int) -> str:
        if self._redis is None:
            return "1"
        raw = await self._redis.get(_VERSION_KEY.format(uid=user_id))
        if raw is None:
            return "1"
        return raw.decode() if isinstance(raw, bytes) else str(raw)

    async def _remember_session(self, ctx: TokenIssueContext, jti: str, ttl: int) -> None:
        if self._redis is None:
            return
        payload = json.dumps(_session_payload(ctx, jti), ensure_ascii=False)
        pipe = self._redis.pipeline()
        pipe.setex(_SESSION_KEY.format(sid=jti), ttl, payload)
        pipe.sadd(_USER_SESSIONS_KEY.format(uid=ctx.uid), jti)
        pipe.expire(_USER_SESSIONS_KEY.format(uid=ctx.uid), ttl + 3600)
        await pipe.execute()

    async def generate_token(self, ctx: TokenIssueContext) -> AuthTokenPair:
        now = int(time.time())
        ttl = _access_ttl(ctx)
        rttl = _refresh_ttl()
        version = await self._get_token_version(ctx.uid)
        jti = uuid.uuid4().hex
        roles = list(ctx.roles or [])

        access_payload = {
            "sub": str(ctx.uid),
            "uid": ctx.uid,
            "name": ctx.username,
            "nickname": ctx.nickname,
            "tenant_id": ctx.tenant_id,
            "role": roles[0] if len(roles) == 1 else roles,
            "roles": roles,
            "is_refresh": False,
            "token_version": version,
            "jti": jti,
            "type": "access",
            "iat": now,
            "exp": now + ttl,
        }
        refresh_payload = {
            "sub": str(ctx.uid),
            "uid": ctx.uid,
            "tenant_id": ctx.tenant_id,
            "is_refresh": True,
            "token_version": version,
            "type": "refresh",
            "iat": now,
            "exp": now + rttl,
        }
        access = jwt.encode(access_payload, self._secret, algorithm=self._alg)
        refresh = jwt.encode(refresh_payload, self._secret, algorithm=self._alg)
        await self._remember_session(ctx, jti, ttl)
        return AuthTokenPair(access_token=access, refresh_token=refresh, expires_in=ttl)

    async def parse_token(self, token: str) -> JWTPayloadSchema | None:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._alg])
            if claims.get("type") == "refresh" or claims.get("is_refresh"):
                return None
            uid = int(claims.get("uid") or claims.get("sub") or 0)
            if uid <= 0:
                return None
            version = await self._get_token_version(uid)
            if str(claims.get("token_version") or "1") != str(version):
                return None
            jti = claims.get("jti")
            if jti and self._redis is not None:
                exists = await self._redis.exists(_SESSION_KEY.format(sid=jti))
                if not exists:
                    return None
            return JWTPayloadSchema(
                sub=str(claims.get("sub") or uid),
                uid=uid,
                name=str(claims.get("name") or ""),
                nickname=str(claims.get("nickname") or ""),
                tenant_id=int(claims.get("tenant_id") or 0),
                role=claims.get("role", "user"),
                roles=list(claims.get("roles") or []),
                is_refresh=False,
                exp=claims.get("exp") or 0,
                token_version=str(claims.get("token_version") or "1"),
                jti=jti,
            )
        except jwt.ExpiredSignatureError:
            logger.debug("JWT access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug("Invalid JWT access token: {}", e)
            return None

    async def validate_token(self, token: str) -> bool:
        return await self.parse_token(token) is not None

    async def resolve_refresh(self, refresh_token: str) -> int | None:
        try:
            claims = jwt.decode(refresh_token, self._secret, algorithms=[self._alg])
            if claims.get("type") != "refresh" and not claims.get("is_refresh"):
                return None
            uid = int(claims.get("uid") or claims.get("sub") or 0)
            if uid <= 0:
                return None
            version = await self._get_token_version(uid)
            if str(claims.get("token_version") or "1") != str(version):
                return None
            return uid
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    async def invalidate_token(self, token: str) -> None:
        """单点登出：删会话；无 jti 时退化为踢该用户全部会话。"""
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self._alg],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError:
            return
        uid = int(claims.get("uid") or claims.get("sub") or 0)
        jti = claims.get("jti")
        if jti and self._redis is not None:
            await self._redis.delete(_SESSION_KEY.format(sid=jti))
            if uid > 0:
                await self._redis.srem(_USER_SESSIONS_KEY.format(uid=uid), jti)
            return
        if uid > 0:
            await self.invalidate_user_sessions(uid)

    async def invalidate_user_sessions(self, user_id: int) -> None:
        if self._redis is None:
            logger.warning("JWT kick requires Redis (token version); user_id={}", user_id)
            return
        await self._redis.incr(_VERSION_KEY.format(uid=user_id))
        sids = await self._redis.smembers(_USER_SESSIONS_KEY.format(uid=user_id))
        if sids:
            keys = [_SESSION_KEY.format(sid=s.decode() if isinstance(s, bytes) else s) for s in sids]
            await self._redis.delete(*keys)
        await self._redis.delete(_USER_SESSIONS_KEY.format(uid=user_id))
        logger.info("User {} all JWT sessions invalidated", user_id)

    async def list_sessions(self) -> list[dict[str, Any]]:
        if self._redis is None:
            return []
        keys = [k async for k in self._redis.scan_iter(match=_SESSION_KEY.format(sid="*"), count=200)]
        if not keys:
            return []
        values = await self._redis.mget(keys)
        out: list[dict[str, Any]] = []
        for raw in values:
            if not raw:
                continue
            try:
                text = raw.decode() if isinstance(raw, bytes) else str(raw)
                out.append(json.loads(text))
            except Exception:
                continue
        out.sort(key=lambda x: x.get("login_time") or "", reverse=True)
        return out

    async def delete_session(self, session_id: str) -> None:
        if self._redis is None:
            return
        raw = await self._redis.get(_SESSION_KEY.format(sid=session_id))
        await self._redis.delete(_SESSION_KEY.format(sid=session_id))
        if not raw:
            return
        try:
            text = raw.decode() if isinstance(raw, bytes) else str(raw)
            info = json.loads(text)
            uid = int(info.get("user_id") or 0)
            if uid > 0:
                await self._redis.srem(_USER_SESSIONS_KEY.format(uid=uid), session_id)
        except Exception:
            pass


# =====================================================================
# Redis-Token 实现（不透明 token，会话全在 Redis）
# =====================================================================


class RedisTokenManager(TokenManager):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def generate_token(self, ctx: TokenIssueContext) -> AuthTokenPair:
        ttl = _access_ttl(ctx)
        rttl = _refresh_ttl()
        access = uuid.uuid4().hex
        refresh = secrets.token_hex(32)
        roles = list(ctx.roles or [])
        claims = {
            "sub": str(ctx.uid),
            "uid": ctx.uid,
            "name": ctx.username,
            "nickname": ctx.nickname,
            "tenant_id": ctx.tenant_id,
            "role": roles[0] if len(roles) == 1 else roles,
            "roles": roles,
            "is_refresh": False,
            "token_version": "1",
            "jti": access,
            "exp": int(time.time()) + ttl,
        }
        session = _session_payload(ctx, access)
        pipe = self._redis.pipeline()
        pipe.setex(_ACCESS_KEY.format(token=access), ttl, ctx.username)
        pipe.setex(_USER_INFO_KEY.format(token=access), ttl, json.dumps(claims, ensure_ascii=False))
        pipe.setex(_SESSION_KEY.format(sid=access), ttl, json.dumps(session, ensure_ascii=False))
        pipe.setex(_REFRESH_KEY.format(token=refresh), rttl, str(ctx.uid))
        pipe.sadd(_USER_TOKENS_KEY.format(uid=ctx.uid), access)
        pipe.expire(_USER_TOKENS_KEY.format(uid=ctx.uid), ttl + 3600)
        await pipe.execute()
        return AuthTokenPair(access_token=access, refresh_token=refresh, expires_in=ttl)

    async def parse_token(self, token: str) -> JWTPayloadSchema | None:
        raw = await self._redis.get(_USER_INFO_KEY.format(token=token))
        if raw is None:
            return None
        try:
            text = raw.decode() if isinstance(raw, bytes) else str(raw)
            claims = json.loads(text)
            return JWTPayloadSchema(
                sub=str(claims.get("sub") or claims.get("uid")),
                uid=int(claims.get("uid") or 0),
                name=str(claims.get("name") or ""),
                nickname=str(claims.get("nickname") or ""),
                tenant_id=int(claims.get("tenant_id") or 0),
                role=claims.get("role", "user"),
                roles=list(claims.get("roles") or []),
                is_refresh=False,
                exp=claims.get("exp") or 0,
                token_version=str(claims.get("token_version") or "1"),
                jti=claims.get("jti") or token,
            )
        except Exception:
            return None

    async def validate_token(self, token: str) -> bool:
        return bool(await self._redis.exists(_ACCESS_KEY.format(token=token)))

    async def resolve_refresh(self, refresh_token: str) -> int | None:
        key = _REFRESH_KEY.format(token=refresh_token)
        uid_raw = await self._redis.get(key)
        if uid_raw is None:
            return None
        await self._redis.delete(key)
        try:
            return int(uid_raw.decode() if isinstance(uid_raw, bytes) else uid_raw)
        except (TypeError, ValueError):
            return None

    async def invalidate_token(self, token: str) -> None:
        info = await self.parse_token(token)
        await self._redis.delete(
            _ACCESS_KEY.format(token=token),
            _USER_INFO_KEY.format(token=token),
            _SESSION_KEY.format(sid=token),
        )
        if info and info.uid:
            await self._redis.srem(_USER_TOKENS_KEY.format(uid=info.uid), token)

    async def invalidate_user_sessions(self, user_id: int) -> None:
        key = _USER_TOKENS_KEY.format(uid=user_id)
        tokens = await self._redis.smembers(key)
        for t in tokens:
            tok = t.decode() if isinstance(t, bytes) else str(t)
            await self._redis.delete(
                _ACCESS_KEY.format(token=tok),
                _USER_INFO_KEY.format(token=tok),
                _SESSION_KEY.format(sid=tok),
            )
        await self._redis.delete(key)
        logger.info("User {} all Redis sessions invalidated", user_id)

    async def list_sessions(self) -> list[dict[str, Any]]:
        keys = [k async for k in self._redis.scan_iter(match=_SESSION_KEY.format(sid="*"), count=200)]
        if not keys:
            return []
        values = await self._redis.mget(keys)
        out: list[dict[str, Any]] = []
        for raw in values:
            if not raw:
                continue
            try:
                text = raw.decode() if isinstance(raw, bytes) else str(raw)
                out.append(json.loads(text))
            except Exception:
                continue
        out.sort(key=lambda x: x.get("login_time") or "", reverse=True)
        return out

    async def delete_session(self, session_id: str) -> None:
        await self.invalidate_token(session_id)


def build_token_manager(redis: Redis | None = None) -> TokenManager:
    """按 SESSION_TYPE 构造 TokenManager。"""
    mode = str(getattr(settings, "SESSION_TYPE", "jwt") or "jwt").strip()
    if mode == "redis-token":
        if redis is None:
            raise CustomException(
                msg="SESSION_TYPE=redis-token 需要启用 Redis",
                code=500,
                status_code=500,
            )
        return RedisTokenManager(redis)
    return JwtTokenManager(redis)
