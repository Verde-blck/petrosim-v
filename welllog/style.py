DARK_QSS = """
QMainWindow { background: #0B1220; }
QWidget { color: #E6EEF7; font-family: Segoe UI, Inter, Arial; font-size: 12px; }

QLabel#BrandTitle { font-size: 18px; font-weight: 800; letter-spacing: 0.5px; }
QLabel#SectionTitle { font-size: 11px; font-weight: 800; color: #9CB3C9; letter-spacing: 1px; }

QFrame#Card {
  background: #0F1A2C;
  border: 1px solid #1C2B45;
  border-radius: 10px;
}

QPushButton {
  background: #13233D;
  border: 1px solid #213A60;
  border-radius: 10px;
  padding: 8px 10px;
  font-weight: 700;
}
QPushButton:hover { background: #182B4D; }
QPushButton:pressed { background: #0E1B31; }
QPushButton:disabled { color: #6F8297; background: #0E1727; border-color: #1A2A44; }

QPushButton#Primary {
  background: #0EA5E9;
  border: 0px;
  color: #07121E;
  font-weight: 900;
}
QPushButton#Primary:hover { background: #38BDF8; }

QComboBox, QLineEdit, QSpinBox {
  background: #0B1526;
  border: 1px solid #1C2B45;
  border-radius: 10px;
  padding: 6px 8px;
}

QSlider::groove:horizontal { height: 6px; background: #162846; border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; background: #0EA5E9; border-radius: 7px; margin: -5px 0; }

QCheckBox { spacing: 10px; }
QCheckBox::indicator {
  width: 18px; height: 18px;
  border-radius: 6px;
  border: 1px solid #1C2B45;
  background: #0B1526;
}
QCheckBox::indicator:checked {
  background: #0EA5E9;
  border: 0px;
}
"""