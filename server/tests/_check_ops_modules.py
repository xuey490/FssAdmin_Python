"""ponytail: 最小自检 — 导入运维相关路由并断言关键路径存在。"""

from __future__ import annotations


def main() -> None:
    from app.api.v1.module_system import CoreRouter, system_router

    core_paths = {getattr(r, "path", "") for r in CoreRouter.routes}
    sys_paths = {getattr(r, "path", "") for r in system_router.routes}

    need_core = [
        "/core/configGroup/list",
        "/core/config/list",
        "/core/config/public/{key}",
        "/core/logs/getLoginLogPageList",
        "/core/logs/getOperLogPageList",
        "/core/email/index",
    ]
    need_sys = [
        "/system/dict/type/list",
        "/system/dict/data/list",
        "/system/attachment/list",
        "/system/attachment-category/list",
    ]
    missing = [p for p in need_core if p not in core_paths] + [p for p in need_sys if p not in sys_paths]
    assert not missing, f"missing routes: {missing}"

    from app.api.v1.module_monitor.core_server import CoreServerRouter

    mon_paths = {getattr(r, "path", "") for r in CoreServerRouter.routes}
    assert "/core/server/monitor" in mon_paths
    assert "/core/server/redis" in mon_paths
    assert "/core/redis/operations" in mon_paths
    print("ok", len(core_paths), "core,", len(sys_paths), "system,", len(mon_paths), "monitor routes")


if __name__ == "__main__":
    main()
