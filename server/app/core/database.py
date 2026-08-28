from fastapi import FastAPI
from redis import exceptions
from redis.asyncio import Redis
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.config.setting import settings
from app.core.base_model import MappedBase
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.sql_echo import install_sql_echo


def _pin_mysql_session_tz(engine: Engine | AsyncEngine) -> None:
    """每条连接 SET time_zone，跟随 .env TIMEZONE。"""
    from app.config.setting import settings as cfg
    from app.core.timezone import mysql_time_zone

    if cfg.DATABASE_TYPE != "mysql":
        return
    sync_eng = getattr(engine, "sync_engine", engine)
    offset = mysql_time_zone()

    @event.listens_for(sync_eng, "connect")
    def _set_tz(dbapi_conn, _connection_record) -> None:  # noqa: ANN001
        cur = dbapi_conn.cursor()
        try:
            cur.execute(f"SET time_zone = '{offset}'")
        finally:
            cur.close()


def create_engine_and_session(
    db_url: str | None = None,
) -> tuple[Engine, sessionmaker]:
    """
    创建同步数据库引擎和会话工厂。

    参数:
    - db_url (str | None): 数据库连接URL，默认从当前 settings 读取。

    返回:
    - tuple[Engine, sessionmaker]: 同步数据库引擎和会话工厂。
    """
    from app.config.setting import settings as cfg

    if db_url is None:
        db_url = cfg.DB_URI
    try:
        if not cfg.SQL_DB_ENABLE:
            raise CustomException(
                msg="请先开启数据库连接",
                data="请启用 app/config/setting.py: SQL_DB_ENABLE",
            )
        # 同步数据库引擎（自定义 SQL_ECHO_* 时关闭原生 echo，避免重复）
        engine: Engine = create_engine(
            url=db_url,
            echo=cfg.DATABASE_ECHO if not (cfg.SQL_ECHO_CONSOLE or cfg.SQL_ECHO_FILE) else False,
            pool_pre_ping=cfg.POOL_PRE_PING,
            pool_recycle=cfg.POOL_RECYCLE,
        )
        install_sql_echo(engine)
        _pin_mysql_session_tz(engine)
    except Exception as e:
        logger.error(f"❌ 数据库连接失败 {e}")
        raise
    else:
        # 同步数据库会话工厂
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, SessionLocal


def create_async_engine_and_session(
    db_url: str | None = None,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    获取异步数据库会话连接。

    参数:
    - db_url (str | None): 异步数据库 URL，默认取当前配置项 ASYNC_DB_URI。

    返回:
    - tuple[AsyncEngine, async_sessionmaker[AsyncSession]]: 异步数据库引擎和会话工厂。
    """
    from app.config.setting import settings as cfg

    if db_url is None:
        db_url = cfg.ASYNC_DB_URI
    try:
        if not cfg.SQL_DB_ENABLE:
            raise CustomException(
                msg="请先开启数据库连接",
                data="请启用 app/config/setting.py: SQL_DB_ENABLE",
            )
        echo = cfg.DATABASE_ECHO if not (cfg.SQL_ECHO_CONSOLE or cfg.SQL_ECHO_FILE) else False
        # 异步数据库引擎
        if cfg.DATABASE_TYPE == "sqlite":
            async_engine = create_async_engine(
                url=db_url,
                echo=echo,
                echo_pool=cfg.ECHO_POOL,
                pool_pre_ping=cfg.POOL_PRE_PING,
                future=cfg.FUTURE,
                pool_recycle=cfg.POOL_RECYCLE,
            )
        else:
            async_engine = create_async_engine(
                url=db_url,
                echo=echo,
                echo_pool=cfg.ECHO_POOL,
                pool_pre_ping=cfg.POOL_PRE_PING,
                future=cfg.FUTURE,
                pool_recycle=cfg.POOL_RECYCLE,
                pool_size=cfg.POOL_SIZE,
                max_overflow=cfg.MAX_OVERFLOW,
                pool_timeout=cfg.POOL_TIMEOUT,
                pool_use_lifo=cfg.POOL_USE_LIFO,
            )
        install_sql_echo(async_engine)
        _pin_mysql_session_tz(async_engine)
    except Exception as e:
        logger.error(f"❌ 数据库连接失败 {e}")
        raise
    else:
        # 异步数据库会话工厂
        AsyncSessionLocal = async_sessionmaker[AsyncSession](
            bind=async_engine,
            autocommit=cfg.AUTOCOMMIT,
            autoflush=cfg.AUTOFLUSH if cfg.AUTOFETCH is None else cfg.AUTOFETCH,
            expire_on_commit=cfg.EXPIRE_ON_COMMIT,
            class_=AsyncSession,
        )
        return async_engine, AsyncSessionLocal


engine, db_session = create_engine_and_session()
async_engine, async_db_session = create_async_engine_and_session()

# 对齐 phpserver：租户 / 软删 / 审计字段自动处理
from app.core.orm_audit import register_orm_audit  # noqa: E402

register_orm_audit()


async def create_tables() -> None:
    """
    创建数据库表（根据 ORM metadata）。

    返回:
    - None
    """
    async with async_engine.begin() as coon:
        await coon.run_sync(MappedBase.metadata.create_all)


async def drop_tables() -> None:
    """
    删除数据库表（根据 ORM metadata）。

    返回:
    - None
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(MappedBase.metadata.drop_all)


async def redis_connect(app: FastAPI, status: bool) -> Redis | None:
    """
    创建或关闭Redis连接。

    参数:
    - app (FastAPI): FastAPI应用实例。
    - status (bool): 连接状态,True为创建连接,False为关闭连接。

    返回:
    - Redis | None: Redis连接实例,如果连接失败则返回None。
    """
    if not settings.REDIS_ENABLE:
        raise CustomException(
            msg="请先开启Redis连接",
            data="请启用 app/core/config.py: REDIS_ENABLE",
        )

    if status:
        try:
            # 构建 Redis URL：处理用户名和密码的组合情况
            auth_part = ""
            if settings.REDIS_USER and settings.REDIS_PASSWORD:
                auth_part = f"{settings.REDIS_USER}:{settings.REDIS_PASSWORD}@"
            elif settings.REDIS_PASSWORD:
                auth_part = f":{settings.REDIS_PASSWORD}@"
            
            redis_url = f"redis://{auth_part}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB_NAME}"
            rd = await Redis.from_url(
                url=redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=20,
                max_connections=settings.POOL_SIZE,
                socket_timeout=settings.POOL_TIMEOUT,
            )
            app.state.redis = rd
            if await rd.ping():  # pyright: ignore[reportGeneralTypeIssues]
                return rd
        except exceptions.AuthenticationError as e:
            logger.error(f"❌ 数据库 Redis 认证失败: {e}")
            raise
        except exceptions.TimeoutError as e:
            logger.error(f"❌ 数据库 Redis 连接超时: {e}")
            raise
        except exceptions.RedisError as e:
            logger.error(f"❌ 数据库 Redis 连接错误: {e}")
            raise
    else:
        await app.state.redis.close()
        logger.info("✅️ Redis连接已关闭")
