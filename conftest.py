"""pytest 共享 fixture：把"测试要用到的资源"统一在这里准备好"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from simulator.bcm_simulator import BcmSimulator

import can
import cantools
import isotp
import pytest
import udsoncan

CAN_CHANNEL = "vcan0"
UDS_CHANNEL = "uds0"
# 诊断仪（客户端）与 ECU（服务端）的地址必须镜像：一端发 0x7E0，另一端就收 0x7E0
UDS_CLIENT_ADDR = dict(txid=0x7E0, rxid=0x7E8)
DBC_PATH = Path(__file__).parent / "dbc" / "body_control.dbc"


@pytest.fixture
def dut_bus():
    """模拟被测节点（BCM）用的总线"""
    bus = can.Bus(interface="virtual", channel=CAN_CHANNEL)
    yield bus          # yield 之后的代码在测试结束后才执行
    bus.shutdown()     # 不关会在测试结束时报 "was not properly shut down"


@pytest.fixture
def bus():
    """模拟测试仪（Tester）用的总线。和 dut_bus 连同一个通道才能互相收发"""
    bus = can.Bus(interface="virtual", channel=CAN_CHANNEL)
    yield bus
    bus.shutdown()


@pytest.fixture(scope="session")
def dbc():
    """加载 DBC 数据库，整个测试会话只加载一次"""
    return cantools.database.load_file(DBC_PATH)

@pytest.fixture(scope="session")
def bcm():
    """后台运行的车身控制器模拟器，session 级：整个测试期间持续周期发报文。

    注意：用例只要把 bcm 写进参数，模拟器就会启动；不写则不会启动，
    bus.recv() 会直接超时
    """
    sim = BcmSimulator()
    sim.start()
    yield sim          # 测试期间模拟器一直在发报文
    sim.stop()         # 全部测试跑完后关掉

@pytest.fixture(scope="session")
def uds_server():
    """模拟 ECU 的 UDS 服务端（独立线程，跑在 uds0 通道上）"""
    from simulator.uds_server import UdsServer
    srv = UdsServer()
    srv.start()
    yield srv
    srv.stop()

@pytest.fixture
def uds_client():
    """诊断仪（Tester）客户端，走 ISO-TP 与 uds_server 通信"""
    from udsoncan.client import Client
    from udsoncan.connections import PythonIsoTpConnection

    bus = can.Bus(interface="virtual", channel=UDS_CHANNEL)
    addr = isotp.Address(isotp.AddressingMode.Normal_11bits, **UDS_CLIENT_ADDR)
    stack = isotp.CanStack(bus=bus, address=addr)

    config = dict(udsoncan.configs.default_client_config)
    config["data_identifiers"] = {
        0xF190: udsoncan.AsciiCodec(13),   # VIN
        0xF191: udsoncan.AsciiCodec(5),    # 服务端不认这个 DID，用于验证否定响应
    }
    config["request_timeout"] = 3
    # 设为 False，否定响应才会作为返回值交给我们断言，而不是直接抛异常
    config["exception_on_negative_response"] = False

    client = Client(PythonIsoTpConnection(stack), config=config)
    client.open()
    yield client
    client.close()
    bus.shutdown()
