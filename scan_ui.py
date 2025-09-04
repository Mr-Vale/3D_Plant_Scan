import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QComboBox, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QMessageBox, QSpinBox
)
from scan_control import ScanController  # Assumes scan_control.py is in same directory

def detect_cameras():
    # TODO: Replace with actual gphoto2 detection in production
    return [
        ("Canon EOS R50 (usb:001,007)", "usb:001,007"),
        ("Canon EOS 200D (usb:001,008)", "usb:001,008"),
        ("Canon EOS M100 (usb:001,009)", "usb:001,009"),
    ]

AXES = ["Z", "Y", "Oblique"]

class ScanConfigUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Turntable Scan Config")
        self.cameras = detect_cameras()
        self.axis_assignments = {}
        self.scan_controller = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        axis_grid = QGridLayout()
        axis_grid.addWidget(QLabel("Assign Cameras to Axes:"), 0, 0, 1, 2)
        self.axis_dropdowns = {}
        for i, axis in enumerate(AXES):
            axis_grid.addWidget(QLabel(f"{axis} Axis:"), i+1, 0)
            combo = QComboBox()
            combo.addItem("None")
            for cam_name, cam_port in self.cameras:
                combo.addItem(cam_name, cam_port)
            combo.currentIndexChanged.connect(self.update_assignments)
            axis_grid.addWidget(combo, i+1, 1)
            self.axis_dropdowns[axis] = combo
        layout.addLayout(axis_grid)

        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle per Photo (degrees):"))
        self.angle_spin = QSpinBox()
        self.angle_spin.setRange(1, 90)
        self.angle_spin.setValue(10)
        self.angle_spin.valueChanged.connect(self.update_calculations)
        angle_layout.addWidget(self.angle_spin)
        layout.addLayout(angle_layout)

        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Scan Label:"))
        self.label_edit = QLineEdit("scan1")
        label_layout.addWidget(self.label_edit)
        layout.addLayout(label_layout)

        self.photo_stats = QLabel("")
        layout.addWidget(self.photo_stats)
        self.update_calculations()

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Scan")
        self.start_btn.clicked.connect(self.save_and_start_scan)
        btn_layout.addWidget(self.start_btn)
        self.stop_btn = QPushButton("Stop Scan")
        self.stop_btn.clicked.connect(self.stop_scan)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def update_assignments(self):
        self.axis_assignments = {axis: self.axis_dropdowns[axis].currentData()
                                 for axis in AXES
                                 if self.axis_dropdowns[axis].currentText() != "None"}
        self.update_calculations()

    def update_calculations(self):
        self.update_assignments()
        angle = self.angle_spin.value()
        num_cams = len(self.axis_assignments)
        if angle == 0 or num_cams == 0:
            self.photo_stats.setText("Select angle and assign at least one camera.")
        else:
            photos_per_camera = 360 // angle
            total_photos = photos_per_camera * num_cams
            self.photo_stats.setText(
                f"Photos per camera: {photos_per_camera} | Total photos: {total_photos}"
            )

    def save_and_start_scan(self):
        self.update_assignments()
        if not self.axis_assignments:
            QMessageBox.warning(self, "Error", "Please assign at least one camera to an axis.")
            return
        config = {
            "scan_label": self.label_edit.text(),
            "angle_per_photo": self.angle_spin.value(),
            "axes": self.axis_assignments,
            "cameras": [
                {"axis": axis, "port": port}
                for axis, port in self.axis_assignments.items()
            ],
            "photos_per_camera": 360 // self.angle_spin.value(),
            "total_photos": (360 // self.angle_spin.value()) * len(self.axis_assignments),
            "step_delay": 0.1
        }
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        QMessageBox.information(self, "Scan Started", "Config saved. Scan starting...")
        self.start_scan(config)

    def start_scan(self, config):
        axes = list(config["axes"].keys())
        camera_map = config["axes"]
        self.scan_controller = ScanController(
            angle_per_photo=config["angle_per_photo"],
            cameras=axes,
            camera_map=camera_map,
            delay=config["step_delay"]
        )
        self.scan_controller.perform_scan(label=config["scan_label"])

    def stop_scan(self):
        if self.scan_controller:
            # Implement proper stop logic in ScanController
            self.scan_controller.stop_scan()
            QMessageBox.information(self, "Scan Stopped", "Scan has been stopped.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScanConfigUI()
    window.show()
    sys.exit(app.exec_())