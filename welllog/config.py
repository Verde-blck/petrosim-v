from dataclasses import dataclass


@dataclass(frozen=True)
class Branding:
    app_name: str = "PETROSIM V — SKOLTECH RESERVOIR INTELLIGENCE"
    short_name: str = "PETROSIM V"
    org: str = "SKOLTECH RESERVOIR INTELLIGENCE"


@dataclass
class AppConfig:
    branding: Branding = Branding()

    # Serial settings (ignored in SIM mode)
    port: str = "COM3"
    baud: int = 115200

    # Plot/UI
    ui_fps: int = 25  # UI refresh rate (Hz)
    ring_capacity: int = 20000  # number of samples stored in memory

    # Depth model (used if incoming depth_mm is missing but step_count is present)
    mm_per_step: float = 0.05  # set from your stepper mechanics

    # Filtering
    smooth_window: int = 1  # 1 = off, 3/5/7 recommended when noisy

    # Logging
    log_dir: str = "runs"