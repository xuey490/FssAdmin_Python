import os
from typing import Annotated

import typer
import uvicorn
from alembic.config import Config
from fastapi import FastAPI

from alembic import command
from app.common.enums import EnvironmentEnum
from app.core.logger import logger
from app.utils.banner import worship

fssadmin_cli = typer.Typer()
alembic_cfg = Config("alembic.ini")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例并完成日志、中间件、路由与静态资源注册。

    返回:
    - FastAPI: 已配置生命周期的应用对象。
    """
    from app.config.setting import get_settings
    from app.init_app import lifespan, register_exceptions, register_files, register_middlewares, register_routers, reset_api_docs

    # 必须用 get_settings()：模块顶层 settings 可能在 --env 切换前已冻结
    app = FastAPI(**get_settings().FASTAPI_CONFIG, lifespan=lifespan)
    # 注册异常处理器
    register_exceptions(app)
    # 注册中间件
    register_middlewares(app)
    # 注册路由
    register_routers(app)
    # 注册静态文件
    register_files(app)
    # 重设API文档
    reset_api_docs(app)
    return app


# typer.Option是非必填；typer.Argument是必填
@fssadmin_cli.command(
    name="run",
    help="启动 FssAdmin 服务, 运行 uv run main.py run --env=dev 不加参数默认 dev 环境",
)
def run(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    按指定环境加载配置并启动 Uvicorn（开发环境开启 reload）。

    参数:
    - env (EnvironmentEnum): 运行环境，对应 `--env`。

    返回:
    - None
    """

    # 设置环境变量（必须在 import settings 之前，确保加载正确环境）
    os.environ["ENVIRONMENT"] = env.value

    # 重新加载配置，使新的 env 文件生效
    from app.config.setting import reload_settings

    reloaded_settings = reload_settings()

    typer.secho(
        message="FssAdmin 服务启动",
        fg=typer.colors.GREEN,
    )
    logger.info(worship(env.value))

    # 启动uvicorn服务
    uvicorn.run(
        app="main:create_app",
        host=reloaded_settings.SERVER_HOST,
        port=reloaded_settings.SERVER_PORT,
        reload=env.value == EnvironmentEnum.DEV.value,
        factory=True,
        log_config=None,
    )

@fssadmin_cli.command(
    name="revision",
    help="生成新的 Alembic 迁移脚本, 运行 python main.py revision --env=dev",
)
def revision(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    使用 Alembic 自动生成迁移脚本（autogenerate）。

    参数:
    - env (EnvironmentEnum): 运行环境，用于加载对应数据库模型元数据。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import reload_settings

    reload_settings()
    command.revision(alembic_cfg, autogenerate=True, message="迁移脚本")
    typer.echo("迁移脚本已生成")


@fssadmin_cli.command(
    name="upgrade",
    help="应用最新的 Alembic 迁移, 运行 python main.py upgrade --env=dev",
)
def upgrade(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    将数据库升级到 Alembic 最新版本（head）。

    参数:
    - env (EnvironmentEnum): 运行环境。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import reload_settings

    reload_settings()
    command.upgrade(alembic_cfg, "head")
    typer.echo("所有迁移已应用。")


if __name__ == "__main__":
    fssadmin_cli()
