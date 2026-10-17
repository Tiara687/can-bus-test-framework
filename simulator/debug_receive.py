"""总线监听小工具：启动 BCM 模拟器，把收到的前 5 条报文和相邻间隔打出来

用例失败时先跑它，能立刻区分"模拟器没在发"还是"用例自己写错了"

用法（必须在项目根目录）：
    python simulator/debug_receive.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import can

from simulator.bcm_simulator import BcmSimulator


def main():
    sim = BcmSimulator()
    sim.start()
    print("模拟器已启动，开始接收...\n")

    # 监听总线必须和模拟器连同一个通道，否则一条也收不到
    listener = can.Bus(interface="virtual", channel="vcan0")
    timestamps = []
    count = 0

    try:
        while count < 5:
            msg = listener.recv(timeout=2.0)
            if msg is None:
                print("2 秒内没收到东西 —— 模拟器没在发！")
                break
            count += 1
            timestamps.append(msg.timestamp)
            gap = "" if len(timestamps) < 2 else \
                f"  间隔 {(timestamps[-1] - timestamps[-2]) * 1000:.1f} ms"
            print(f"第 {count} 条: ID=0x{msg.arbitration_id:X} 数据={msg.data.hex()}{gap}")
    finally:
        sim.stop()
        listener.shutdown()

    if len(timestamps) >= 2:
        total = (timestamps[-1] - timestamps[0]) * 1000 / (len(timestamps) - 1)
        print(f"\n平均周期: {total:.1f} ms（期望 100ms 左右）")


if __name__ == "__main__":
    main()
