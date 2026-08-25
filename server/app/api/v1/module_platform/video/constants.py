"""视频下载任务状态常量。"""

# 元数据 status
META_PENDING = 0
META_OK = 1
META_FAIL = -1

# job status
JOB_QUEUED = 0
JOB_RUNNING = 1
JOB_PAUSED = 2
JOB_DONE = 3
JOB_FAILED = -1
JOB_STOPPED = -2

# Redis
REDIS_CTRL_PREFIX = "video:dl:ctrl:"
REDIS_PROGRESS_PREFIX = "video:dl:progress:"
REDIS_LOCK_PREFIX = "video:dl:lock:"
REDIS_META_QUEUE = "video:meta:queue"
CTRL_RUN = "run"
CTRL_PAUSE = "pause"
CTRL_STOP = "stop"

# 合法状态迁移（用于自检）
JOB_TRANSITIONS: dict[int, set[int]] = {
    JOB_QUEUED: {JOB_RUNNING, JOB_STOPPED},
    JOB_RUNNING: {JOB_PAUSED, JOB_STOPPED, JOB_DONE, JOB_FAILED},
    JOB_PAUSED: {JOB_QUEUED, JOB_STOPPED},
    JOB_FAILED: {JOB_QUEUED},
    JOB_STOPPED: {JOB_QUEUED},
    JOB_DONE: {JOB_QUEUED},
}


def can_transition(from_status: int, to_status: int) -> bool:
    return to_status in JOB_TRANSITIONS.get(from_status, set())
