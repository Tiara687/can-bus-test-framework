"""车身状态报文（0x100）的基础用例：虚拟总线收发 + DBC 编解码 + 枚举值映射"""
import can
import pytest

# BodyStatus 报文 ID：DBC 里定义的 256 = 0x100
BODY_STATUS_ID = 0x100


def test_bus_can_deliver_message(dut_bus, bus):
    """用例 1：总线上能收到指定 ID 的报文（最基础的通信链路验证）"""
    dut_bus.send(
        can.Message(arbitration_id=BODY_STATUS_ID, data=b"\x00" * 8, is_extended_id=False)
    )
    msg = bus.recv(timeout=1.0)
    assert msg is not None, "1 秒内没有收到任何报文，总线链路不通"
    assert msg.arbitration_id == BODY_STATUS_ID


def test_encode_and_decode_speed(dbc):
    """用例 2：DBC 编码后再解码，车速信号值能还原"""
    msg_def = dbc.get_message_by_frame_id(BODY_STATUS_ID)
    data = msg_def.encode(
        {
            "VehicleSpeed": 60.0,
            "BatteryVoltage": 12.5,
            "DriverDoor": 1,
            "PassengerDoor": 0,
            "LowBeam": 0,
            "HighBeam": 0,
        }
    )
    decoded = msg_def.decode(data)
    assert decoded["VehicleSpeed"] == pytest.approx(60.0)


@pytest.mark.parametrize("door_value,expected", [(0, "Closed"), (1, "Open")])
def test_door_signal_choices(dbc, door_value, expected):
    """用例 3（parametrize 演示）：车门信号的枚举值映射是否正确"""
    msg_def = dbc.get_message_by_frame_id(BODY_STATUS_ID)
    data = msg_def.encode(
        {
            "VehicleSpeed": 0.0,
            "BatteryVoltage": 12.5,
            "DriverDoor": door_value,
            "PassengerDoor": 0,
            "LowBeam": 0,
            "HighBeam": 0,
        }
    )
    decoded = msg_def.decode(data, decode_choices=False)
    # decode_choices=False 时返回原始数值；打开则返回 VAL_ 里定义的字符串
    assert decoded["DriverDoor"] == door_value
