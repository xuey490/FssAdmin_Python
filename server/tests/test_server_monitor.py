"""ponytail: server/monitor 跳过会卡住的非本地盘。"""

from types import SimpleNamespace

from app.api.v1.module_monitor.core_server import _collect_monitor, _is_local_fixed_partition


def test_skip_cdrom_remote_empty() -> None:
    assert _is_local_fixed_partition(SimpleNamespace(fstype="CDFS", opts="cdrom", device="D:\\")) is False
    assert _is_local_fixed_partition(SimpleNamespace(fstype="NTFS", opts="remote", device="Z:\\")) is False
    assert _is_local_fixed_partition(SimpleNamespace(fstype="cifs", opts="rw", device="//nas/share")) is False
    assert _is_local_fixed_partition(SimpleNamespace(fstype="", opts="rw,fixed", device="E:\\")) is False
    assert _is_local_fixed_partition(SimpleNamespace(fstype="NTFS", opts="rw,fixed", device="C:\\")) is True


def test_collect_monitor_is_fast() -> None:
    import time

    t0 = time.perf_counter()
    data = _collect_monitor()
    elapsed = time.perf_counter() - t0
    assert "memory" in data and "phpEnv" in data and "disk" in data
    assert elapsed < 1.0, f"monitor collect too slow: {elapsed:.3f}s"


if __name__ == "__main__":
    test_skip_cdrom_remote_empty()
    test_collect_monitor_is_fast()
    print("ok")
