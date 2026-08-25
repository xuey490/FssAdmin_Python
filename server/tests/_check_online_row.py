"""ponytail: online 会话字段对齐 web camelCase。"""

from app.api.v1.module_monitor.online.service import session_to_row


def main() -> None:
    row = session_to_row(
        {
            "session_id": "abc123",
            "user_name": "admin",
            "dept_name": "研发部",
            "ipaddr": "127.0.0.1",
            "login_location": "内网IP",
            "os": "Windows",
            "browser": "Chrome",
            "login_time": "2026-07-18 18:00:00",
            "user_id": 1,
            "tenant_id": 1,
        }
    )
    assert row["tokenId"] == "abc123"
    assert row["userName"] == "admin"
    assert row["deptName"] == "研发部"
    assert row["loginLocation"] == "内网IP"
    assert row["loginTime"] == "2026-07-18 18:00:00"
    print("online row ok")


if __name__ == "__main__":
    main()
