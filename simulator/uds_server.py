import threading,time
import can,isotp

class UdsServer(threading.Thread):
    def __init__(self,channel="uds0",verbose=False):
        super().__init__(daemon=True)
        self.verbose = verbose
        self.bus = can.Bus(interface="virtual",
        channel=channel)
        addr = isotp.Address(isotp.AddressingMode.
        Normal_11bits,txid=0x7E8,rxid=0x7E0)
        self.stack = isotp.CanStack(bus=self.bus,
        address=addr)
        self.running = True

    def run(self):
        while self.running:
            self.stack.process()
            if self.stack.available():        # 先问"有没有收完整一帧"
                payload = self.stack.recv()   # 再取出来存进变量
                resp = self.handle(payload)
                if self.verbose:
                    print(f"  [ECU] 收到 {payload.hex():<16} → 回 {resp.hex()}")
                self.stack.send(resp)
            time.sleep(0.002)

    def handle(self,payload):
        sid = payload[0]
        if sid == 0x10:
            return bytes([0x50,0x03,0x00,0x32,0x01,0xF4])
        elif sid == 0x22:
            did_high = payload[1]      # DID 是两个字节，0xF190 里 F1 是高字节
            did_low = payload[2]
            if did_high == 0xF1 and did_low == 0x90:
                return bytes([0x62,0xF1,0x90]) + b"VIN1234567890"
            else:
                return bytes([0x7f,0x22,0x31])
        elif sid == 0x19:
            return bytes([0x59,0x02,0x00,0x00,0x00,0x01,0x2F])
        else:
            return bytes([0x7F,sid,0x11])

    def stop(self):
        """停止后台线程，让 run() 里的 while 循环退出。"""
        self.running = False
        self.join(timeout=2.0)
        self.bus.shutdown() 