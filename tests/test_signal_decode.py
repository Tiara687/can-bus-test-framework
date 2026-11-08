"""验证信号链路：物理值经 DBC 编码上总线、再解回来后必须保持一致

此处有三个重点：
1. encode 必须把 6 个信号全给齐，少一个报 EncodeError: The signal "..." is required
2. 浮点不能用 == 比较（0.1 精度问题），用 pytest.approx
3. decode 默认返回枚举字符串（如 'Open'），要数字需 decode_choices=False

车速在 DBC 里 factor=0.1，所以总线上传的是 600，解回来才是 60.0 km/h
"""
import can
import pytest

BODY_STATUS_ID = 0x100


def test_decode_vehicle_speed(dbc, dut_bus, bus):
    """编码车速 60.0 发出去，对面解回来应仍是 60.0。"""
    msg_def = dbc.get_message_by_frame_id(BODY_STATUS_ID)

    data = msg_def.encode({
        "VehicleSpeed": 60.0,
        "BatteryVoltage": 12.5,
        "DriverDoor": 0,
        "PassengerDoor": 0,
        "LowBeam": 0,
        "HighBeam": 0,
    }, strict=True)

    dut_bus.send(can.Message(arbitration_id=BODY_STATUS_ID, data=data, is_extended_id=False))
    msg = bus.recv(timeout=1.0)
    decoded = msg_def.decode(msg.data)

    assert decoded["VehicleSpeed"] == pytest.approx(60.0)
