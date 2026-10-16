"""周期抖动测试：验证周期报文的实际发送间隔符合 DBC 定义的 100ms ±10%。

判定区间定为 90~110ms（±10%）是行业常见做法：周期报文若偏差过大，
下游控制器（仪表、车身）会出现显示卡顿或误判。
阈值不能写成 0 容差——操作系统调度本身就有毫秒级抖动，会导致用例
时而红时而绿（flaky）。

反面验证：把 bcm_simulator 的 cycle_seconds 改成 0.15，本用例必须变红。
"""
import pytest


def test_body_status_cycle_time(bcm, bus):
    timestamps = []
    while len(timestamps) < 10:
        msg = bus.recv(timeout=2.0)
        if msg is None:
            pytest.fail("2秒内没收到报文")
        if msg.arbitration_id == 0x100:
            timestamps.append(msg.timestamp)
    intervals_ms = []
    for i in range(len(timestamps)-1):
        intervals_ms.append((timestamps[i+1]-timestamps[i])*1000)
    assert len(intervals_ms) >= 9, f"只收到 {len(intervals_ms)} 个间隔，样本不足"
    assert max(intervals_ms) <= 110, f"最慢 {max(intervals_ms):.1f}ms，抖动超标（上限 110ms）"
    assert min(intervals_ms) >= 90, f"最快 {min(intervals_ms):.1f}ms，周期偏快（下限 90ms）"
