"""
模块接口测试 —— 插件模块 - task（任务调度）

动态路由映射：module_task → /task
包含 cronjob（调度器/任务/日志/节点）。

每个接口一个测试用例，覆盖查询 / 新增 / 修改 / 删除 等操作。
"""

from conftest import assert_route
from fastapi.testclient import TestClient

# ============================================================
# /task/cronjob — 调度器与任务
# ============================================================


class TestCronjobScheduler:
    """调度器管理接口。"""

    def test_scheduler_status(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/task/cronjob/job/scheduler/status")

    def test_scheduler_jobs(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/task/cronjob/job/scheduler/jobs")

    def test_scheduler_start(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/task/cronjob/job/scheduler/start")

    def test_scheduler_pause(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/task/cronjob/job/scheduler/pause")

    def test_scheduler_resume(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/task/cronjob/job/scheduler/resume")

    def test_scheduler_console(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/task/cronjob/job/scheduler/console")

    def test_scheduler_sync(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/task/cronjob/job/scheduler/sync")

    def test_scheduler_shutdown(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/task/cronjob/job/scheduler/shutdown")

    def test_scheduler_jobs_clear(self, test_client: TestClient) -> None:
        assert_route(test_client, "DELETE", "/task/cronjob/job/scheduler/jobs/clear")


class TestCronjobTask:
    """任务管理接口。"""

    def test_task_pause(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/task/cronjob/job/task/pause/test_job")

    def test_task_resume(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/task/cronjob/job/task/resume/test_job")

    def test_task_run(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/task/cronjob/job/task/run/test_job")

    def test_task_remove(self, test_client: TestClient) -> None:
        assert_route(test_client, "DELETE", "/task/cronjob/job/task/remove/test_job")


class TestCronjobLog:
    """执行日志接口。"""

    def test_job_log_list(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/task/cronjob/job/log/list")

    def test_job_log_detail(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/task/cronjob/job/log/detail/1")

    def test_job_log_delete(self, test_client: TestClient) -> None:
        assert_route(test_client, "DELETE", "/task/cronjob/job/log/delete", json=[9999])


class TestCronjobNode:
    """节点管理接口。"""

    def test_node_options(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/task/cronjob/node/options")

    def test_node_list(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/task/cronjob/node/list")

    def test_node_detail(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/task/cronjob/node/detail/1")

    def test_node_create(self, test_client: TestClient) -> None:
        assert_route(
            test_client,
            "POST",
            "/task/cronjob/node/create",
            json={"name": "测试节点", "node_type": "http"},
        )

    def test_node_update(self, test_client: TestClient) -> None:
        assert_route(
            test_client,
            "PUT",
            "/task/cronjob/node/update/1",
            json={"name": "更新节点"},
        )

    def test_node_delete(self, test_client: TestClient) -> None:
        assert_route(test_client, "DELETE", "/task/cronjob/node/delete", json=[9999])

    def test_node_execute(self, test_client: TestClient) -> None:
        assert_route(
            test_client,
            "POST",
            "/task/cronjob/node/execute/1",
            json={},
        )

    def test_node_clear(self, test_client: TestClient) -> None:
        assert_route(test_client, "DELETE", "/task/cronjob/node/clear")

    def test_node_status_batch(self, test_client: TestClient) -> None:
        assert_route(
            test_client,
            "PATCH",
            "/task/cronjob/node/status/batch",
            json={"ids": [1], "status": 1},
        )
