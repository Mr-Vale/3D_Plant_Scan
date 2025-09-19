import sys
import os
import subprocess
import json
import math
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QGroupBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSizePolicy, QGridLayout
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
AUTODETECT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cam_autodetect.py')
SCAN_CONTROL_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_control.py')
AXES = ["Z", "Y", "Oblique"]

# Font settings
BASE_FONT_SIZE = 18
SCALE_FACTOR = 1
FONT_SIZE = int(BASE_FONT_SIZE * SCALE_FACTOR)
TITLE_FONT_SIZE = int(FONT_SIZE * 1.10)


# --- LOG RENAMING AT STARTUP ---
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_log.txt')
LOG_PATH_OLD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_log(old).txt')
if os.path.exists(LOG_PATH):
    # If scan_log(old).txt exists, remove it
    if os.path.exists(LOG_PATH_OLD):
        os.remove(LOG_PATH_OLD)
    os.rename(LOG_PATH, LOG_PATH_OLD)
# --- END LOG RENAMING ---


def run_camera_autodetect():
    try:
        subprocess.run(["python3", AUTODETECT_SCRIPT], check=True)
    except Exception as e:
        QMessageBox.warning(None, "Autodetect Error", f"Error running camera autodetect:\n{e}")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

class ScanUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Camera Scan UI")
        self.setFixedSize(700, 900)   # lock window size
        self.move(0, 0)               # top-left corner

        self.setWindowFlags(
            Qt.Window |
            Qt.CustomizeWindowHint |
            Qt.WindowStaysOnTopHint
        )

        self.cameras = []
        self.config = {}
        self.camera_combos = {}
        self.scan_process = None
        self.scan_timer = QTimer()
        self.scan_timer.setInterval(1000)
        self.scan_timer.timeout.connect(self.check_scan_status)

        self.setFont(QFont("Arial", FONT_SIZE))

        self.init_ui()
        self.populate_camera_list(first=True)
        self.update_calculations()

    def set_touch_widget(self, widget, bold=False):
        font = QFont("Arial", FONT_SIZE)
        if bold:
            font.setBold(True)
        widget.setFont(font)
        widget.setMinimumHeight(65)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return widget

    def set_title_label(self, label):
        label.setFont(QFont("Arial", TITLE_FONT_SIZE, QFont.Bold))
        label.setContentsMargins(0, 0, 0, 1) # space below
        return label

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(25)  # More space between sections

        # Scan Configuration Title
        config_title = self.set_title_label(QLabel("Scan Configuration"))
        main_layout.addWidget(config_title)

        # Scan Configuration Inputs
        config_group = QWidget()
        config_layout = QFormLayout()
        config_layout.setSpacing(20)

        # Scan Name (editable, full width)
        self.scan_name_edit = self.set_touch_widget(QLineEdit())
        self.scan_name_edit.setText("my_plant_scan")
        self.scan_name_edit.textChanged.connect(self.on_config_changed)
        self.scan_name_edit.setMinimumWidth(1)
        self.scan_name_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.scan_name_edit.focused = False

        config_layout.addRow(self.set_touch_widget(QLabel("Scan Name:")), self.scan_name_edit)

        # Angle per Photo (editable spinbox)
        self.angle_spin = self.set_touch_widget(QDoubleSpinBox())
        self.angle_spin.setRange(0.5, 180.0)
        self.angle_spin.setSingleStep(0.5)
        self.angle_spin.setValue(10.0)
        self.angle_spin.valueChanged.connect(self.on_config_changed)
        config_layout.addRow(self.set_touch_widget(QLabel("Angle per Photo (degrees):")), self.angle_spin)

        # Calculated outputs
        self.num_photos_label = self.set_touch_widget(QLabel())
        config_layout.addRow(self.set_touch_widget(QLabel("Photos per Camera (per revolution):")), self.num_photos_label)
        self.total_photos_label = self.set_touch_widget(QLabel())
        config_layout.addRow(self.set_touch_widget(QLabel("Total Photos (all cameras):")), self.total_photos_label)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # Camera Assignments Title
        camera_title = self.set_title_label(QLabel("Camera Assignments"))
        main_layout.addWidget(camera_title)

        # Camera selection
        camera_group = QWidget()
        camera_layout = QFormLayout()
        camera_layout.setSpacing(20)
        for axis in AXES:
            combo = self.set_touch_widget(QComboBox())
            combo.addItem("None")
            combo.currentIndexChanged.connect(self.on_camera_assignment_changed)
            self.camera_combos[axis] = combo
            camera_layout.addRow(self.set_touch_widget(QLabel(f"{axis} axis:")), combo)
        camera_group.setLayout(camera_layout)
        main_layout.addWidget(camera_group)

        # Button Title
        button_title = self.set_title_label(QLabel("Controls"))
        main_layout.addWidget(button_title)

        # 4 Buttons In Square Grid
        button_grid = QGridLayout()
        button_grid.setSpacing(20)
        self.refresh_button = self.set_touch_widget(QPushButton("Refresh Cameras"), bold=True)
        self.refresh_button.clicked.connect(self.refresh_cameras)
        self.save_button = self.set_touch_widget(QPushButton("Save Config"), bold=True)
        self.save_button.clicked.connect(self.save_camera_assignments)
        self.start_button = self.set_touch_widget(QPushButton("Start Scan"), bold=True)
        self.start_button.clicked.connect(self.start_scan)
        self.stop_button = self.set_touch_widget(QPushButton("Stop Scan"), bold=True)
        self.stop_button.clicked.connect(self.stop_scan)
        self.stop_button.setEnabled(False)

        # Make buttons taller
        buttons = [self.refresh_button, self.save_button, self.start_button, self.stop_button]
        for i, btn in enumerate(buttons):
            btn.setMinimumSize(0, 120)  # height increased to 120px (adjust as needed)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            button_grid.addWidget(btn, i // 2, i % 2)

        main_layout.addLayout(button_grid)

        self.setLayout(main_layout)

    def populate_camera_list(self, first=False):
        run_camera_autodetect()

        self.config = load_config()
        self.cameras = self.config.get("cameras", [])

        # Set scan name and angle from config if present
        self.scan_name_edit.setText(str(self.config.get("scan_label", "my_plant_scan")))
        self.angle_spin.setValue(float(self.config.get("angle_per_photo", 10.0)))

        # Gather camera ports for options
        available_ports = ["None","Fake Camera"] + [cam["port"] for cam in self.cameras]
        axes_config = self.config.get("axes", {})

        for axis, combo in self.camera_combos.items():
            current_selection = axes_config.get(axis, "None")
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(available_ports)
            # Set selection to previous assignment if present, else "None"
            index = combo.findText(current_selection)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

        self.update_calculations()

    def refresh_cameras(self):
        self.populate_camera_list()
        QMessageBox.information(self, "Cameras Refreshed",
            f"Detected cameras:\n" +
            "\n".join([f'{cam["axis"]}: {cam["port"]}' for cam in self.cameras])
        )

    def on_camera_assignment_changed(self):
        self.update_config_from_ui()
        self.update_calculations()

    def on_config_changed(self):
        self.update_config_from_ui()
        self.update_calculations()

    def update_config_from_ui(self):
        # Update config from UI fields
        self.config["scan_label"] = self.scan_name_edit.text()
        self.config["angle_per_photo"] = float(self.angle_spin.value())
        axes = self.config.get("axes", {})
        for axis, combo in self.camera_combos.items():
            value = combo.currentText()
            axes[axis] = value if value != "None" else "None"
        self.config["axes"] = axes
        # Keep cameras list for config consistency
        self.config["cameras"] = [
            {"axis": axis, "port": port}
            for axis, port in axes.items() if port != "None"
        ]

    def update_calculations(self):
        angle = float(self.angle_spin.value())
        if angle <= 0:
            self.num_photos_label.setText("Invalid angle")
            self.total_photos_label.setText("")
            return

        photos_per_camera = int(math.ceil(360.0 / angle))
        self.num_photos_label.setText(str(photos_per_camera))

        selected_cameras = [axis for axis, combo in self.camera_combos.items() if combo.currentText() != "None"]
        total_photos = photos_per_camera * len(selected_cameras)
        self.total_photos_label.setText(f"{total_photos}")

    def save_camera_assignments(self):
        self.update_config_from_ui()
        save_config(self.config)
        QMessageBox.information(self, "Config Saved", "Camera assignments saved to config.json.")

    def release_motor(self):
        try:
            subprocess.run(["python3", SCAN_CONTROL_SCRIPT, "--cleanup"])
        except Exception as e:
            print(f"Error releasing motor: {e}")

    def start_scan(self):
        self.save_camera_assignments()
        if self.scan_process is not None and self.scan_process.poll() is None:
            QMessageBox.warning(self, "Scan Already Running", "A scan is already running. Stop it first.")
            return
        try:
            self.scan_process = subprocess.Popen(["python3", SCAN_CONTROL_SCRIPT])
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.scan_timer.start()
        except Exception as e:
            QMessageBox.warning(self, "Scan Error", f"Could not start scan:\n{e}")

    def stop_scan(self):
        if self.scan_process is None or self.scan_process.poll() is not None:
            QMessageBox.information(self, "No Scan Running", "No scan process is running.")
            self.release_motor()
            return
        try:
            self.scan_process.terminate()
            self.scan_timer.stop()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            QMessageBox.information(self, "Scan Stopped", "Scan stopped!")
            self.release_motor()
        except Exception as e:
            QMessageBox.warning(self, "Stop Error", f"Could not stop scan:\n{e}")
            self.release_motor()

    def check_scan_status(self):
        if self.scan_process is not None and self.scan_process.poll() is not None:
            self.scan_timer.stop()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.scan_process = None
            QMessageBox.information(self, "Scan Finished", "Scan finished!")

    def closeEvent(self, event):
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScanUI()
    window.show()
    sys.exit(app.exec_())