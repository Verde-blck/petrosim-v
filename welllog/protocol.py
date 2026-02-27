from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class Sample:
    ts_ms: int
    depth_mm: float
    sp_mv: float
    res_raw: float
    ind_raw: float
    seq: int = 0
    status: int = 0


def parse_line(line: str, mm_per_step: float) -> Optional[Sample]:
    """
    Accepts either:
      1) JSON line:
         {"ts_ms":123,"depth_mm":10.0,"sp_mv":1.2,"res_raw":100,"ind_raw":0.3,"seq":7,"status":0}
         OR {"ts_ms":123,"step":200,"sp_mv":1.2,"res_raw":100,"ind_raw":0.3}
      2) CSV-like:
         ts_ms,depth_mm,sp_mv,res_raw,ind_raw,seq,status
         or
         ts_ms,step,sp_mv,res_raw,ind_raw,seq,status

    Returns None if the line can’t be parsed.
    """
    line = line.strip()
    if not line:
        return None

    # JSON
    if line.startswith("{") and line.endswith("}"):
        try:
            obj = json.loads(line)

            ts_ms = int(obj["ts_ms"])
            seq = int(obj.get("seq", 0))
            status = int(obj.get("status", 0))

            sp_mv = float(obj.get("sp_mv", 0.0))
            res_raw = float(obj.get("res_raw", 0.0))
            ind_raw = float(obj.get("ind_raw", 0.0))

            if "depth_mm" in obj:
                depth_mm = float(obj["depth_mm"])
            elif "step" in obj:
                depth_mm = float(obj["step"]) * float(mm_per_step)
            else:
                return None

            return Sample(
                ts_ms=ts_ms,
                depth_mm=depth_mm,
                sp_mv=sp_mv,
                res_raw=res_raw,
                ind_raw=ind_raw,
                seq=seq,
                status=status,
            )
        except Exception:
            return None

    # CSV-ish fallback
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 5:
        return None

    try:
        ts_ms = int(parts[0])
        depth_or_step = float(parts[1])
        sp_mv = float(parts[2])
        res_raw = float(parts[3])
        ind_raw = float(parts[4])
        seq = int(parts[5]) if len(parts) > 5 and parts[5] else 0
        status = int(parts[6]) if len(parts) > 6 and parts[6] else 0

        # NOTE:
        # If you send steps instead of depth_mm, you can either:
        # - send depth_mm already computed, OR
        # - change this line to: depth_mm = depth_or_step * mm_per_step
        depth_mm = depth_or_step

        return Sample(
            ts_ms=ts_ms,
            depth_mm=depth_mm,
            sp_mv=sp_mv,
            res_raw=res_raw,
            ind_raw=ind_raw,
            seq=seq,
            status=status,
        )
    except Exception:
        return None