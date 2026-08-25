"""ponytail: TokenManager 发签 / 解析 / version 踢人冒烟。"""

from __future__ import annotations

import asyncio
import os

os.environ.setdefault("ENVIRONMENT", "dev")

from app.core.token_manager import JwtTokenManager, TokenIssueContext


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    async def get(self, key: str):
        return self.kv.get(key)

    async def setex(self, key: str, _ttl: int, value: str):
        self.kv[key] = value

    async def incr(self, key: str):
        self.kv[key] = str(int(self.kv.get(key, "0") or 0) + 1)
        return int(self.kv[key])

    async def exists(self, key: str):
        return 1 if key in self.kv else 0

    async def delete(self, *keys: str):
        n = 0
        for k in keys:
            if k in self.kv:
                del self.kv[k]
                n += 1
            if k in self.sets:
                del self.sets[k]
                n += 1
        return n

    async def sadd(self, key: str, *members: str):
        self.sets.setdefault(key, set()).update(members)
        return len(members)

    async def srem(self, key: str, *members: str):
        s = self.sets.get(key)
        if not s:
            return 0
        n = 0
        for m in members:
            if m in s:
                s.discard(m)
                n += 1
        return n

    async def smembers(self, key: str):
        return set(self.sets.get(key, set()))

    async def expire(self, key: str, _ttl: int):
        return True

    def pipeline(self):
        return _FakePipe(self)

    def scan_iter(self, match: str = "*", count: int = 200):
        prefix = match.rstrip("*")

        async def _gen():
            for k in list(self.kv):
                if k.startswith(prefix):
                    yield k

        return _gen()

    async def mget(self, keys):
        return [self.kv.get(k) for k in keys]


class _FakePipe:
    def __init__(self, r: _FakeRedis) -> None:
        self.r = r
        self.ops: list = []

    def setex(self, key, ttl, value):
        self.ops.append(("setex", key, ttl, value))
        return self

    def sadd(self, key, *members):
        self.ops.append(("sadd", key, members))
        return self

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        for op in self.ops:
            if op[0] == "setex":
                await self.r.setex(op[1], op[2], op[3])
            elif op[0] == "sadd":
                await self.r.sadd(op[1], *op[2])
            elif op[0] == "expire":
                await self.r.expire(op[1], op[2])
        self.ops.clear()


async def _main() -> None:
    redis = _FakeRedis()
    tm = JwtTokenManager(redis)  # type: ignore[arg-type]
    ctx = TokenIssueContext(
        uid=42,
        username="admin",
        nickname="管理员",
        tenant_id=1,
        roles=["admin"],
        is_super=True,
        access_ttl=3600,
    )
    pair = await tm.generate_token(ctx)
    assert pair.access_token and pair.refresh_token
    claims = await tm.parse_token(pair.access_token)
    assert claims is not None and claims.uid == 42 and claims.tenant_id == 1

    await tm.invalidate_user_sessions(42)
    assert await tm.parse_token(pair.access_token) is None

    pair2 = await tm.generate_token(ctx)
    assert await tm.parse_token(pair2.access_token) is not None
    await tm.invalidate_token(pair2.access_token)
    assert await tm.parse_token(pair2.access_token) is None
    print("token_manager ok")


if __name__ == "__main__":
    asyncio.run(_main())
