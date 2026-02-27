from __future__ import annotations
import queue
import threading
import time
from typing import Optional

import serial  # pyserial

from .protocol import parse_line, Sample
from .simulator import Simulator


class SerialReader(threading.Thread):
    def __init__(self, port: str, baud: int, out_q: queue.Queue[str], stop_event: threading.Event):
        super().__init__(daemon=True)
        self.port = port
        self.baud = baud
        self.out_q = out_q
        self.stop_event = stop_event
        self._ser: Optional[serial.Serial] = None

    def run(self):
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=0.2)
        except Exception as e:
            self.out_q.put(f"__ERROR__:{e}")
            return

        buf = b""
        while not self.stop_event.is_set():
            try:
                chunk = self._ser.read(4096)
                if not chunk:
                    continue
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        self.out_q.put(line.decode("utf-8", errors="ignore"))
                    except Exception:
                        pass
            except Exception as e:
                self.out_q.put(f"__ERROR__:{e}")
                break

        try:
            if self._ser:
                self._ser.close()
        except Exception:
            pass


class SimReader(threading.Thread):
    def __init__(self, out_q: queue.Queue[Sample], stop_event: threading.Event, hz: float = 20.0):
        super().__init__(daemon=True)
        self.out_q = out_q
        self.stop_event = stop_event
        self.hz = hz
        self.sim = Simulator()

    def run(self):
        dt = 1.0 / self.hz
        while not self.stop_event.is_set():
            self.out_q.put(self.sim.next_sample())
            time.sleep(dt)