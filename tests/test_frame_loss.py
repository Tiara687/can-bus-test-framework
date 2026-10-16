"""丢帧统计：在固定时间窗内，应该收到的报文是否都收到了。

BodyStatus（0x100）周期 100ms，2 秒窗口内期望收到 20 条。
真实车上丢帧就是"仪表偶尔卡顿""车门状态偶尔不刷新"的元凶。

阈值取 10% 而非 0%：真实总线存在仲裁、错误帧、CPU 占用等影响，
判定条件必须留合理余量，否则用例会变成时而红时而绿的 flaky 用例。

反面验证：把 bcm_simulator 的 cycle_seconds 改成 0.2，本用例必须变红。
"""
import time


def test_frame_loss(bcm, bus):
    start = time.time()
    count = 0
    while time.time() - start < 2.0:
        msg = bus.recv(timeout=0.5)
        if msg is not None and msg.arbitration_id == 0x100:
            count += 1
    expected = 20                      # 2 秒 / 0.1 秒
    loss_rate = (expected - count) / expected
    assert loss_rate <= 0.10,f"丢帧率为{loss_rate:0.1%}，超过10%阈值"