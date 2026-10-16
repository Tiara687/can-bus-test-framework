"""UDS 诊断服务测试（ISO 14229 / ISO-TP）。

请求与正响应的对应关系：

    0x10 会话控制   10 03        → 50 03 00 32 01 F4
    0x22 读 DID     22 F1 90     → 62 F1 90 <13字节VIN>
    0x19 读 DTC     19 02 FF     → 59 02 <可用性掩码> <DTC记录...>

否定响应统一格式：7F <服务ID> <否定码>
    0x11 serviceNotSupported      服务不支持
    0x31 requestOutOfRange        请求参数超范围（本文件用它验证未知 DID）

注意：客户端 config 里必须声明用到的 DID，且设置
exception_on_negative_response=False，否则否定响应会直接抛异常，
拿不到 resp.positive 供断言。
"""


def test_change_session_should_succeed(uds_server, uds_client):
    """0x10 切换到扩展会话（0x03），正响应首字节应回显会话类型。"""
    resp = uds_client.change_session(3)
    assert resp.positive, f"切换会话失败，否定码 {resp.code_name}"
    assert resp.data[0] == 0x03


def test_read_vin_should_return_vin(uds_server, uds_client):
    """0x22 读 VIN（DID 0xF190）。

    resp.data 前两字节是 DID 本身（F1 90），真正的 VIN 从第 3 字节开始。
    """
    resp = uds_client.read_data_by_identifier(0xF190)
    assert resp.positive, f"读 VIN 失败，否定码 {resp.code_name}"
    assert resp.data[2:].decode("ascii") == "VIN1234567890"


def test_read_dtc_should_return_one_fault(uds_server, uds_client):
    """0x19 按状态掩码读 DTC，服务端返回 1 条故障（P0001，状态 0x2F）。"""
    resp = uds_client.get_dtc_by_status_mask(0xFF)
    assert resp.positive, f"读 DTC 失败，否定码 {resp.code_name}"
    assert resp.service_data.dtc_count == 1
    assert resp.service_data.dtcs[0].id == 0x000001


def test_unsupported_did_should_be_rejected(uds_server, uds_client):
    """读取服务端不认识的 DID（0xF191），应返回否定响应 7F 22 31。"""
    resp = uds_client.read_data_by_identifier(0xF191)
    assert not resp.positive
    assert resp.code == 0x31      # requestOutOfRange
