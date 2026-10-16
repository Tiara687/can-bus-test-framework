"""
UDS 手动调试脚本：不经过 pytest，直接把每一次诊断请求/响应的原始字节打出来。

用法（必须在项目根目录跑）：
    python simulator/debug_uds.py

它做的事：手动启动 ECU 服务端 → 建一个诊断客户端 → 发 4 个请求 → 把每一次
请求/响应打印出来。不用 pytest，一眼就能看到总线上到底跑的是什么字节。
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import can, isotp, udsoncan
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client

from simulator.uds_server import UdsServer


def main():
    # 1) 启动模拟 ECU（verbose=True 会打印它收到/回复的每一个字节）
    srv = UdsServer(verbose=True)
    srv.start()
    time.sleep(0.2)

    # 2) 建诊断仪客户端（txid/rxid 与服务端交叉）
    bus = can.Bus(interface="virtual", channel="uds0")
    addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=0x7E0, rxid=0x7E8)
    stack = isotp.CanStack(bus=bus, address=addr)

    config = dict(udsoncan.configs.default_client_config)
    config["data_identifiers"] = {
        0xF190: udsoncan.AsciiCodec(13),   # VIN
        0xF191: udsoncan.AsciiCodec(5),    # 服务端不认这个 DID，用来测否定响应
    }
    config["request_timeout"] = 3
    config["exception_on_negative_response"] = False

    client = Client(PythonIsoTpConnection(stack), config=config)
    client.open()

    # 3) 依次发四个诊断请求
    print("\n--- 0x10 切换扩展会话 ---")
    r = client.change_session(3)
    print(f"    positive={r.positive}  原始={r.get_payload().hex()}")

    print("\n--- 0x22 读 VIN (0xF190) ---")
    r = client.read_data_by_identifier(0xF190)
    print(f"    positive={r.positive}  VIN={r.data[2:].decode('ascii')}")

    print("\n--- 0x19 读 DTC (状态掩码 FF) ---")
    r = client.get_dtc_by_status_mask(0xFF)
    sd = r.service_data
    print(f"    positive={r.positive}  DTC数量={sd.dtc_count}")
    for d in sd.dtcs:
        print(f"      DTC id=0x{d.id:06x}  status=0x{d.status.get_byte_as_int():02x}")

    print("\n--- 0x22 读一个服务端不认的 DID (0xF191)，验证否定响应 ---")
    r = client.read_data_by_identifier(0xF191)
    print(f"    positive={r.positive}  否定码=0x{r.code:02x} ({r.code_name})")

    client.close()
    bus.shutdown()
    srv.stop()
    srv.join(timeout=2)
    print("\n调试结束")


if __name__ == "__main__":
    main()
