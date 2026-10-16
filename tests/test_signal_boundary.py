"""车速信号的等价类划分 + 边界值分析。

DBC 里 VehicleSpeed 定义范围是 0~400（factor=0.1）：

    ┌─ 无效等价类 ─┬────── 有效等价类 ──────┬─ 无效等价类 ─┐
    │     -1       │   0  ...  200  ...  400 │     401      │
    └──────────────┴─────────────────────────┴──────────────┘
                   ↑边界                     ↑边界

本文件三条用例分别覆盖：有效等价类、无效等价类（必须报错）、
以及"严格模式被关掉时越界值会泄漏到总线上"这一风险。
"""
import pytest
from cantools.database.errors import EncodeError


@pytest.mark.parametrize("speed", [0, 200, 400])
def test_valid_speed_should_encode(dbc,speed):
    msg_def = dbc.get_message_by_frame_id(0x100)
    data = msg_def.encode({
                           "VehicleSpeed": speed, 
                           "BatteryVoltage":0,
                           "DriverDoor":0,
                           "PassengerDoor":0,
                           "LowBeam":0,
                           "HighBeam":0
    })
    assert msg_def.decode(data)["VehicleSpeed"] == pytest.approx(speed)


@pytest.mark.parametrize("speed", [-1, 401, 400.1])
def test_invalid_speed_should_be_rejected(dbc, speed):
    msg_def = dbc.get_message_by_frame_id(0x100)

    with pytest.raises(EncodeError):
        msg_def.encode({
            "VehicleSpeed": speed,
            "BatteryVoltage": 0,
            "DriverDoor": 0,
            "PassengerDoor": 0,
            "LowBeam": 0,
            "HighBeam": 0,
        }, strict=True)


def test_out_of_range_value_leaks_when_strict_disabled(dbc):
    """strict=False 时 cantools 不校验 DBC 范围，越界值会被编上总线。

    这条用例把风险固化下来：谁关掉严格模式，它立刻变红。
    """
    msg_def = dbc.get_message_by_frame_id(0x100)
    data = msg_def.encode({
        "VehicleSpeed": 401,
        "BatteryVoltage": 0,
        "DriverDoor": 0,
        "PassengerDoor": 0,
        "LowBeam": 0,
        "HighBeam": 0,
    }, strict=False)
    decoded = msg_def.decode(data)
    assert decoded["VehicleSpeed"] == 401, f"越界值被放过，解码后是 {decoded['VehicleSpeed']}"



