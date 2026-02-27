from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from typing import Optional

from .protocol import Sample
from .config import Branding


@dataclass
class SessionInfo:
    path: str
    started_at: float
    created_at_str: str


class SessionLogger:
    def __init__(self, log_dir: str, branding: Branding):
        self.log_dir = log_dir
        self.branding = branding
        self._file = None
        self._writer = None
        self.info: Optional[SessionInfo] = None

    def start(self) -> SessionInfo:
        os.makedirs(self.log_dir, exist_ok=True)
        created_at = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{self.branding.short_name.replace(' ', '-')}-run-{created_at}.csv"
        path = os.path.join(self.log_dir, filename)

        f = open(path, "w", newline="", encoding="utf-8")
        writer = csv.writer(f)

        # Metadata header rows (CSV-friendly)
        writer.writerow(["# project", self.branding.app_name])
        writer.writerow(["# created_at", created_at])
        writer.writerow([])

        # Data header
        writer.writerow(["ts_ms", "depth_mm", "sp_mv", "res_raw", "ind_raw", "seq", "status"])

        self._file = f
        self._writer = writer
        self.info = SessionInfo(path=path, started_at=time.time(), created_at_str=created_at)
        return self.info

    def log(self, s: Sample) -> None:
        if not self._writer:
            return
        self._writer.writerow([s.ts_ms, s.depth_mm, s.sp_mv, s.res_raw, s.ind_raw, s.seq, s.status])

    def stop(self) -> None:
        if self._file:
            try:
                self._file.flush()
            finally:
                self._file.close()
        self._file = None
        self._writer = None
        self.info = None