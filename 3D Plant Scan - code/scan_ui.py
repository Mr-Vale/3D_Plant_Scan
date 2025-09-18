import sys
import os
import subprocess
import json
import math
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QGroupBox, QFormLayout, QLineEdit, QDoubleSpinBox
)
from PyQt5.QtCore import QTimer

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
AUTODETECT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cam_autodetect.py')
SCAN_CONTROL_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_control.py')
AXES = ["Z", "Y", "Oblique"]

PHOTO_TIME_SEC = 5  # Estimated time per photo

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
        self.resize(520, 420)
        self.cameras = []
        self.config = {}
        self.camera_combos = {}
        self.scan_process = None
        self.scan_timer = QTimer()
        self.scan_timer.setInterval(1000)
        self.scan_timer.timeout.connect(self.check_scan_status)

        self.init_ui()
        self.populate_camera_list(first=True)
        self.update_calculations()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Scan Configuration Inputs
        config_group = QGroupBox("Scan Configuration")
        config_layout = QFormLayout()

        # Scan Name (editable)
        self.scan_name_edit = QLineEdit()
        self.scan_name_edit.setText("my_plant_scan")
        self.scan_name_edit.textChanged.connect(self.on_config_changed)
        config_layout.addRow("Scan Name:", self.scan_name_edit)

        # Angle per Photo (editable spinbox)
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(0.5, 180.0)
        self.angle_spin.setSingleStep(0.5)
        self.angle_spin.setValue(10.0)
        self.angle_spin.valueChanged.connect(self.on_config_changed)
        config_layout.addRow("Angle per Photo (degrees):", self.angle_spin)

        # Calculated outputs
        self.num_photos_label = QLabel()
        config_layout.addRow("Photos per Camera (per revolution):", self.num_photos_label)
        self.total_photos_label = QLabel()
        config_layout.addRow("Total Photos (all cameras):", self.total_photos_label)
        self.estimated_time_label = QLabel()
        config_layout.addRow("Estimated Scan Time:", self.estimated_time_label)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # Camera selection
        camera_group = QGroupBox("Camera Assignments")
        camera_layout = QFormLayout()
        for axis in AXES:
            combo = QComboBox()
            combo.addItem("None")
            combo.currentIndexChanged.connect(self.on_camera_assignment_changed)
            self.camera_combos[axis] = combo
            camera_layout.addRow(f"{axis} axis:", combo)
        camera_group.setLayout(camera_layout)
        main_layout.addWidget(camera_group)

        # Control buttons (refresh/save at top, start/stop at bottom)
        button_layout_top = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Cameras")
        self.refresh_button.clicked.connect(self.refresh_cameras)
        button_layout_top.addWidget(self.refresh_button)
        self.save_button = QPushButton("Save Config")
        self.save_button.clicked.connect(self.save_camera_assignments)
        button_layout_top.addWidget(self.save_button)
        main_layout.addLayout(button_layout_top)

        main_layout.addStretch()

        button_layout_bottom = QHBoxLayout()
        self.start_button = QPushButton("Start Scan")
        self.start_button.clicked.connect(self.start_scan)
        button_layout_bottom.addWidget(self.start_button)
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.clicked.connect(self.stop_scan)
        self.stop_button.setEnabled(False)
        button_layout_bottom.addWidget(self.stop_button)
        main_layout.addLayout(button_layout_bottom)

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
            self.estimated_time_label.setText("")
            return

        photos_per_camera = int(math.ceil(360.0 / angle))
        self.num_photos_label.setText(str(photos_per_camera))

        selected_cameras = [axis for axis, combo in self.camera_combos.items() if combo.currentText() != "None"]
        total_photos = photos_per_camera * len(selected_cameras)
        self.total_photos_label.setText(f"{total_photos}")

        estimated_seconds = total_photos * PHOTO_TIME_SEC
        mins, secs = divmod(estimated_seconds, 60)
        hours, mins = divmod(mins, 60)
        self.estimated_time_label.setText(
            f"{hours:.0f}h {mins:.0f}m {secs:.0f}s ({estimated_seconds:.0f} seconds)"
        )

    def save_camera_assignments(self):
        self.update_config_from_ui()
        save_config(self.config)
        QMessageBox.information(self, "Config Saved", "Camera assignments saved to config.json.")

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
            QMessageBox.information(self, "Scan Started", "Scan started!")
        except Exception as e:
            QMessageBox.warning(self, "Scan Error", f"Could not start scan:\n{e}")

    def stop_scan(self):
        if self.scan_process is None or self.scan_process.poll() is not None:
            QMessageBox.information(self, "No Scan Running", "No scan process is running.")
            return
        try:
            self.scan_process.terminate()
            self.scan_timer.stop()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            QMessageBox.information(self, "Scan Stopped", "Scan stopped!")
        except Exception as e:
            QMessageBox.warning(self, "Stop Error", f"Could not stop scan:\n{e}")

    def check_scan_status(self):
        if self.scan_process is not None and self.scan_process.poll() is not None:
            self.scan_timer.stop()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            QMessageBox.information(self, "Scan Finished", "Scan finished!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScanUI()
    window.show()
    sys.exit(app.exec_())