"""丢帧统计：在一个固定时间窗里，该收到的报文是不是都收到了

BodyStatus（0x100）周期 100ms，2 秒窗口内应该收到 20 条
车上真丢帧的表现就是仪表偶尔卡顿、车门状态偶尔不刷新

阈值取 10% 而不是 0，是因为总线上有仲裁、错误帧、CPU 占用这些干扰，
卡死了这个用例会一会红一会绿，那就没法用了

反面验证：把 bcm_simulator 的 cycle_seconds 改成 0.2，本用例必须变红
"""
import time

BODY_STATUS_ID = 0x100
WINDOW_SECONDS = 2.0


def test_frame_loss(bcm, bus, dbc):
    # 期望条数不写死在代码里，改成从 DBC 定义的报文周期（GenMsgCycleTime）算出来，
    # 这样 DBC 里把周期改了，用例会自己跟着变
    cycle_ms = dbc.get_message_by_frame_id(BODY_STATUS_ID).cycle_time
    expected = int(WINDOW_SECONDS * 1000 / cycle_ms)

    start = time.time()
    count = 0
    while time.time() - start < WINDOW_SECONDS:
        msg = bus.recv(timeout=0.5)
        if msg is not None and msg.arbitration_id == BODY_STATUS_ID:
            count += 1

    loss_rate = (expected - count) / expected
    assert loss_rate <= 0.10,f"丢帧率为{loss_rate:0.1%}，超过10%阈值"