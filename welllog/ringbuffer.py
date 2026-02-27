from __future__ import annotations
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class RingData:
    ts_ms: np.ndarray
    depth_mm: np.ndarray
    sp_mv: np.ndarray
    res_raw: np.ndarray
    ind_raw: np.ndarray
    seq: np.ndarray
    status: np.ndarray


class RingBuffer:
    def __init__(self, capacity: int):
        self.capacity = int(capacity)
        self._size = 0
        self._idx = 0

        self.ts_ms = np.zeros(self.capacity, dtype=np.int64)
        self.depth_mm = np.zeros(self.capacity, dtype=np.float64)
        self.sp_mv = np.zeros(self.capacity, dtype=np.float64)
        self.res_raw = np.zeros(self.capacity, dtype=np.float64)
        self.ind_raw = np.zeros(self.capacity, dtype=np.float64)
        self.seq = np.zeros(self.capacity, dtype=np.int64)
        self.status = np.zeros(self.capacity, dtype=np.int64)

    def append(self, s):
        i = self._idx
        self.ts_ms[i] = s.ts_ms
        self.depth_mm[i] = s.depth_mm
        self.sp_mv[i] = s.sp_mv
        self.res_raw[i] = s.res_raw
        self.ind_raw[i] = s.ind_raw
        self.seq[i] = s.seq
        self.status[i] = s.status

        self._idx = (self._idx + 1) % self.capacity
        self._size = min(self._size + 1, self.capacity)

    def clear(self):
        self._size = 0
        self._idx = 0

    def snapshot(self) -> RingData:
        """
        Returns ordered arrays from oldest->newest.
        """
        n = self._size
        if n == 0:
            return RingData(
                ts_ms=np.array([], dtype=np.int64),
                depth_mm=np.array([], dtype=np.float64),
                sp_mv=np.array([], dtype=np.float64),
                res_raw=np.array([], dtype=np.float64),
                ind_raw=np.array([], dtype=np.float64),
                seq=np.array([], dtype=np.int64),
                status=np.array([], dtype=np.int64),
            )

        start = (self._idx - n) % self.capacity
        if start + n <= self.capacity:
            sl = slice(start, start + n)
            return RingData(
                ts_ms=self.ts_ms[sl].copy(),
                depth_mm=self.depth_mm[sl].copy(),
                sp_mv=self.sp_mv[sl].copy(),
                res_raw=self.res_raw[sl].copy(),
                ind_raw=self.ind_raw[sl].copy(),
                seq=self.seq[sl].copy(),
                status=self.status[sl].copy(),
            )

        # Wrap
        a = slice(start, self.capacity)
        b = slice(0, (start + n) % self.capacity)
        return RingData(
            ts_ms=np.concatenate([self.ts_ms[a], self.ts_ms[b]]),
            depth_mm=np.concatenate([self.depth_mm[a], self.depth_mm[b]]),
            sp_mv=np.concatenate([self.sp_mv[a], self.sp_mv[b]]),
            res_raw=np.concatenate([self.res_raw[a], self.res_raw[b]]),
            ind_raw=np.concatenate([self.ind_raw[a], self.ind_raw[b]]),
            seq=np.concatenate([self.seq[a], self.seq[b]]),
            status=np.concatenate([self.status[a], self.status[b]]),
        )