from __future__ import annotations

import queue
import time
import threading
from typing import Optional

from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg

from .config import AppConfig
from .protocol import parse_line, Sample
from .ringbuffer import RingBuffer
from .session import SessionLogger
from .workers import SerialReader, SimReader


def moving_average(x, w: int):
    if w <= 1 or len(x) < w:
        return x
    import numpy as np
    c = np.convolve(x, np.ones(w) / w, mode="valid")
    pad = len(x) - len(c)
    return np.concatenate([x[:pad], c])


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg
        self.branding = cfg.branding

        self.setWindowTitle(self.branding.app_name)
        self.resize(1100, 700)

        self.buffer = RingBuffer(cfg.ring_capacity)
        self.session = SessionLogger(cfg.log_dir, self.branding)

        # --- Central UI
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)

        # Branding header
        brand = QtWidgets.QLabel(self.branding.app_name)
        brand.setStyleSheet("font-size: 18px; font-weight: 800;")
        layout.addWidget(brand)

        # Controls row
        controls = QtWidgets.QHBoxLayout()
        layout.addLayout(controls)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["SIM", "SERIAL"])
        controls.addWidget(QtWidgets.QLabel("Mode:"))
        controls.addWidget(self.mode_combo)

        self.port_edit = QtWidgets.QLineEdit(cfg.port)
        self.port_edit.setFixedWidth(120)
        controls.addWidget(QtWidgets.QLabel("Port:"))
        controls.addWidget(self.port_edit)

        self.baud_edit = QtWidgets.QLineEdit(str(cfg.baud))
        self.baud_edit.setFixedWidth(120)
        controls.addWidget(QtWidgets.QLabel("Baud:"))
        controls.addWidget(self.baud_edit)

        self.smooth_spin = QtWidgets.QSpinBox()
        self.smooth_spin.setRange(1, 101)
        self.smooth_spin.setSingleStep(2)
        self.smooth_spin.setValue(cfg.smooth_window)
        controls.addWidget(QtWidgets.QLabel("Smooth window:"))
        controls.addWidget(self.smooth_spin)

        self.btn_connect = QtWidgets.QPushButton("Connect")
        self.btn_disconnect = QtWidgets.QPushButton("Disconnect")
        self.btn_disconnect.setEnabled(False)

        self.btn_start = QtWidgets.QPushButton("Start Recording")
        self.btn_stop = QtWidgets.QPushButton("Stop Recording")
        self.btn_stop.setEnabled(False)

        self.btn_clear = QtWidgets.QPushButton("Clear Plot")

        controls.addWidget(self.btn_connect)
        controls.addWidget(self.btn_disconnect)
        controls.addSpacing(20)
        controls.addWidget(self.btn_start)
        controls.addWidget(self.btn_stop)
        controls.addSpacing(20)
        controls.addWidget(self.btn_clear)
        controls.addStretch(1)

        # Status text area
        self.status_label = QtWidgets.QLabel("Idle")
        layout.addWidget(self.status_label)

        # Plot area: 3 tracks, shared Y axis (depth)
        pg.setConfigOptions(antialias=True)
        self.graphics = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics, 1)

        self.plt_sp = self.graphics.addPlot(row=0, col=0, title="SP (mV) vs Depth")
        self.plt_res = self.graphics.addPlot(row=0, col=1, title="Resistivity (raw) vs Depth")
        self.plt_ind = self.graphics.addPlot(row=0, col=2, title="Induction (raw) vs Depth")

        for p in (self.plt_sp, self.plt_res, self.plt_ind):
            p.invertY(True)  # depth increases downward
            p.showGrid(x=True, y=True, alpha=0.3)
            p.setLabel("left", "Depth", units="mm")

        # Curves: points for now (fast + simple). You can switch to pen lines later.
        self.curve_sp = self.plt_sp.plot([], [], pen=None, symbol="o", symbolSize=3)
        self.curve_res = self.plt_res.plot([], [], pen=None, symbol="o", symbolSize=3)
        self.curve_ind = self.plt_ind.plot([], [], pen=None, symbol="o", symbolSize=3)

        self.plt_sp.setLabel("bottom", "SP", units="mV")
        self.plt_res.setLabel("bottom", "Res", units="raw")
        self.plt_ind.setLabel("bottom", "Ind", units="raw")

        # --- runtime state
        self.serial_line_q: queue.Queue[str] = queue.Queue(maxsize=5000)
        self.sample_q: queue.Queue[Sample] = queue.Queue(maxsize=5000)

        self.stop_event: Optional[threading.Event] = None
        self.reader_thread = None
        self.sim_thread = None

        self.connected = False
        self.recording = False

        self.last_ui_update = time.time()
        self.last_sample_time = time.time()
        self.sample_count = 0
        self.last_depth = 0.0
        self.last_error: Optional[str] = None

        # UI refresh timer
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(int(1000 / cfg.ui_fps))
        self.timer.timeout.connect(self.on_tick)
        self.timer.start()

        # Signals
        self.btn_connect.clicked.connect(self.connect_source)
        self.btn_disconnect.clicked.connect(self.disconnect_source)
        self.btn_start.clicked.connect(self.start_recording)
        self.btn_stop.clicked.connect(self.stop_recording)
        self.btn_clear.clicked.connect(self.clear_plot)

        self.mode_combo.currentTextChanged.connect(self.on_mode_change)
        self.on_mode_change(self.mode_combo.currentText())

    def on_mode_change(self, mode: str):
        is_serial = (mode == "SERIAL")
        self.port_edit.setEnabled(is_serial)
        self.baud_edit.setEnabled(is_serial)

    def connect_source(self):
        if self.connected:
            return

        self.stop_event = threading.Event()
        self.last_error = None

        mode = self.mode_combo.currentText().strip().upper()

        if mode == "SIM":
            # SIM should never touch serial ports
            self.sim_thread = SimReader(self.sample_q, self.stop_event, hz=20.0)
            self.sim_thread.start()
            self.status_label.setText(f"{self.branding.short_name}: SIM mode running (20 Hz)")

        else:
            # SERIAL mode
            port = self.port_edit.text().strip()
            baud = int(self.baud_edit.text().strip())

            self.reader_thread = SerialReader(port, baud, self.serial_line_q, self.stop_event)
            self.reader_thread.start()
            self.status_label.setText(f"{self.branding.short_name}: Connecting {port}@{baud} ...")

        self.connected = True
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)

    def disconnect_source(self):
        if not self.connected:
            return

        if self.stop_event:
            self.stop_event.set()

        self.reader_thread = None
        self.sim_thread = None
        self.stop_event = None
        self.connected = False

        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.status_label.setText(f"{self.branding.short_name}: Disconnected")

    def start_recording(self):
        if self.recording:
            return
        info = self.session.start()
        self.recording = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText(f"{self.branding.short_name}: Recording → {info.path}")

    def stop_recording(self):
        if not self.recording:
            return
        self.session.stop()
        self.recording = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText(f"{self.branding.short_name}: Recording stopped")

    def clear_plot(self):
        self.buffer.clear()
        self.status_label.setText(f"{self.branding.short_name}: Cleared plot")

    def _drain_serial_lines(self, max_lines: int = 2000):
        drained = 0
        while drained < max_lines:
            try:
                line = self.serial_line_q.get_nowait()
            except queue.Empty:
                break

            if line.startswith("__ERROR__:"):
                self.last_error = line.replace("__ERROR__:", "", 1)
                drained += 1
                continue

            s = parse_line(line, self.cfg.mm_per_step)
            if s:
                try:
                    self.sample_q.put_nowait(s)
                except queue.Full:
                    pass
            drained += 1

    def on_tick(self):
        # Pull from serial thread into sample queue
        if self.connected and self.mode_combo.currentText() == "SERIAL":
            self._drain_serial_lines()

        # Drain samples into ring buffer
        drained = 0
        while drained < 5000:
            try:
                s = self.sample_q.get_nowait()
            except queue.Empty:
                break

            self.buffer.append(s)
            self.last_sample_time = time.time()
            self.sample_count += 1
            self.last_depth = s.depth_mm

            if self.recording:
                self.session.log(s)

            drained += 1

        # Plot update
        data = self.buffer.snapshot()
        if len(data.depth_mm) > 0:
            w = int(self.smooth_spin.value())
            depth = data.depth_mm
            sp = moving_average(data.sp_mv, w)
            res = moving_average(data.res_raw, w)
            ind = moving_average(data.ind_raw, w)

            self.curve_sp.setData(sp, depth)
            self.curve_res.setData(res, depth)
            self.curve_ind.setData(ind, depth)

        # Status bar update (once per second)
        now = time.time()
        dt = now - self.last_ui_update
        if dt >= 1.0:
            rate = self.sample_count / dt
            self.sample_count = 0
            self.last_ui_update = now

            health = "OK"
            if self.last_error:
                health = f"ERROR: {self.last_error}"
            elif self.connected and (now - self.last_sample_time) > 1.5:
                health = "No data..."

            self.statusBar().showMessage(
                f"{self.branding.short_name} | Depth: {self.last_depth:.1f} mm | Rate: {rate:.1f} Hz | {health}"
            )


def run_app() -> int:
    cfg = AppConfig()
    app = QtWidgets.QApplication([])
    win = MainWindow(cfg)
    win.show()
    return app.exec()