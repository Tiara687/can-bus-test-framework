import time
from pathlib import Path
from threading import Event, Thread

import can
import cantools

BODY_STATUS_ID = 0x100
DBC_PATH = Path(__file__).parent.parent / "dbc" / "body_control.dbc"
class BcmSimulator:
    def __init__(self,channel="vcan0",cycle_seconds=0.1):
        self.db = cantools.database.load_file(DBC_PATH)
        self.bus = can.Bus(interface="virtual",channel=channel)
        self.cycle = cycle_seconds
        self.state = {"VehicleSpeed": 60.0, 
                           "BatteryVoltage":0,
                           "DriverDoor":0,
                           "PassengerDoor":0,
                           "LowBeam":0,
                           "HighBeam":0,
                           }
        self._stop = Event()
        self._thread = None

    def start(self):
        self._thread = Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self.bus.shutdown()

    def _loop(self):
        msg_def = self.db.get_message_by_frame_id(BODY_STATUS_ID)
        while not self._stop.is_set():
            # strict=True 让 cantools 校验信号值有没有超出 DBC 定义的范围
            # 关掉的话越界值会被静默编上总线，风险见 test_signal_boundary.py
            data = msg_def.encode(self.state, strict=True)
            self.bus.send(
                 can.Message(
                                arbitration_id = BODY_STATUS_ID,data = data,is_extended_id = False
                            )
            )
           
            time.sleep(self.cycle)
