"""ponytail: assert global oper-log middleware wiring + whitelist."""

from __future__ import annotations

from app.config.setting import settings
from app.core.operation_log import should_record_oper_log


def main() -> None:
    assert should_record_oper_log("POST", "/system/user/create")
    assert should_record_oper_log("DELETE", "/api/system/dept/delete/1")
    assert should_record_oper_log("POST", "/core/email/destroy")
    assert should_record_oper_log("POST", "/core/database/table/optimize")
    assert should_record_oper_log("PUT", "/core/config")
    assert not should_record_oper_log("GET", "/system/user/list")
    assert not should_record_oper_log("POST", "/core/login")
    assert not should_record_oper_log("POST", "/api/core/login")
    assert not should_record_oper_log("DELETE", "/core/logs/deleteLoginLog")
    assert not should_record_oper_log("POST", "/core/captcha")

    names = [m for m in settings.MIDDLEWARE_LIST if m]
    assert any(m and m.endswith("OperationLogMiddleware") for m in names), names
    print("ok", "middlewares=", len(names))


if __name__ == "__main__":
    main()
