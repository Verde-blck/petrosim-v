from __future__ import annotations
import math
import random
import time
from .protocol import Sample


class Simulator:
    """
    Generates plausible demo-like curves vs depth for testing UI.
    """
    def __init__(self):
        self.seq = 0
        self.depth_mm = 0.0
        self.start = time.time()

    def next_sample(self) -> Sample:
        self.seq += 1
        t = time.time() - self.start

        # move downward at 5 mm per tick (adjust)
        self.depth_mm += 5.0

        # Fake SP: small mV drift + layer steps
        sp = 0.5 * math.sin(t * 0.5) + 0.15 * random.uniform(-1, 1)
        if 2000 < self.depth_mm < 3500:
            sp += 1.2
        if 6000 < self.depth_mm < 7500:
            sp -= 0.9

        # Fake resistivity: higher in "sand" zones, lower in "shale"
        res = 80 + 10 * math.sin(t * 0.2) + 4 * random.uniform(-1, 1)
        if 2500 < self.depth_mm < 3300:
            res += 60
        if 6500 < self.depth_mm < 7200:
            res += 40

        # Fake induction: subtle variations + noise
        ind = 0.2 + 0.05 * math.sin(t * 0.7) + 0.03 * random.uniform(-1, 1)

        ts_ms = int((time.time()) * 1000)
        return Sample(ts_ms=ts_ms, depth_mm=self.depth_mm, sp_mv=sp, res_raw=res, ind_raw=ind, seq=self.seq, status=0)