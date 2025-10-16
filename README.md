# 3D Plant Scan

A simple, Python-based multi-camera scanning rig controller for photographing plants (or other objects) on a motorized turntable for photogrammetry. It includes a touch-friendly PyQt5 UI for assigning cameras to axes, setting scan parameters, and starting/stopping automated capture while the turntable rotates.

- UI: PyQt5 (touch-friendly layout)
- Camera assignment: up to three axes (Z, Y, Oblique)
- Automated capture: turntable steps and triggers photos per angle
- Config persistence: JSON-based configuration
- Headless mode: run the scan controller without the UI
- Desktop launcher: optional .desktop file for convenience

---

## Contents

- cam_autodetect.py — Detects connected cameras and writes results into the config.
- config.json — Configuration file for the UI and scan controller.
- photo_control.py — Photo capture logic (per-axis/per-camera orchestration).
- scan_control.py — Main scanning controller (coordinates turntable + camera shots).
- scan_ui.py — Touch-friendly PyQt5 UI to configure and control scanning.
- turntable_control.py — Turntable control logic.
- drivers/ — Hardware driver helpers (if needed for your setup).
- 3D_Plant_Scan.desktop — Optional desktop shortcut launcher.
- update_repo.sh — Utility script to update your local folder from the GitHub repo without deleting extra local files.
- 3D Plant Scan - code/ — A copy of the core scripts (keep using the top-level versions unless you specifically want the nested copy).

License: see LICENSE.

---

## Requirements

- Python 3 (recommended 3.9+)
- PyQt5 (for the UI)
- Platform: Linux (e.g., Raspberry Pi OS), with permissions to access cameras and your motor driver interface.

Install PyQt5 (choose one):
- System package (Debian/Raspberry Pi OS): 
  - sudo apt update && sudo apt install -y python3-pyqt5
- Or via pip (if using a virtual environment):
  - python3 -m venv venv
  - source venv/bin/activate
  - pip install PyQt5

Note: Additional camera or motor control dependencies depend on your hardware (e.g., udev rules, camera drivers, GPIO libraries, USB permissions). Ensure your OS can see and access your cameras before using the app.

---

## Quick Start

1) Clone the repo
- git clone https://github.com/Mr-Vale/3D_Plant_Scan.git
- cd 3D_Plant_Scan

2) (Optional) Create and activate a virtual environment, then install PyQt5
- python3 -m venv venv
- source venv/bin/activate
- pip install PyQt5

3) Launch the UI
- python3 scan_ui.py
  - The UI will:
    - Run camera autodetect (cam_autodetect.py)
    - Let you assign detected camera ports to axes (Z, Y, Oblique)
    - Let you set the Angle per Photo (degrees). The UI shows calculated photos per camera and total photos.

4) Start a scan
- In the UI, tap “Save Config” then “Start Scan”.
- The UI will start scan_control.py in the background, which coordinates turntable movement and triggers photos at each angle step.
- Tap “Stop Scan” to end early; the UI will attempt cleanup (releasing the motor).

5) Headless mode (optional)
- You can run the controller without the UI:
  - python3 scan_control.py
- Cleanup only (release the motor, if supported by your drivers):
  - python3 scan_control.py --cleanup

---

## Configuration

The application uses config.json in the repository directory to store your settings. The UI reads and writes this file automatically; you can also edit it manually.

Common fields:
- scan_label: String label for the current scan (used in output naming).
- angle_per_photo: Degrees the turntable rotates between shots (e.g., 10.0).
- axes: Mapping of axis names to assigned camera ports, e.g. "Z", "Y", "Oblique".
- cameras: A flattened list derived from assignments; generally maintained by the UI.

Example config.json:
```json
{
  "scan_label": "my_plant_scan",
  "angle_per_photo": 10.0,
  "axes": {
    "Z": "usb-port-1",
    "Y": "None",
    "Oblique": "usb-port-2"
  },
  "cameras": [
    { "axis": "Z", "port": "usb-port-1" },
    { "axis": "Oblique", "port": "usb-port-2" }
  ]
}
```

Notes:
- Use the UI to set angle and camera assignments; it will keep the cameras list consistent.
- “None” means no camera is assigned to that axis.

---

## Directory Structure

```
3D_Plant_Scan/
├── 3D_Plant_Scan.desktop         # optional desktop launcher
├── cam_autodetect.py             # camera discovery helper
├── config.json                   # app configuration
├── drivers/                      # hardware driver helpers (if applicable)
├── photo_control.py              # photo capture coordination
├── scan_control.py               # main scan orchestrator
├── scan_ui.py                    # PyQt5 UI (touch-friendly)
├── turntable_control.py          # turntable motion control
├── update_repo.sh                # update local copy from GitHub (no deletions)
├── cube_icon.png                 # app icon
├── LICENSE
└── 3D Plant Scan - code/         # copy of core scripts (use top-level by default)
```

---

## Desktop Launcher (Optional)

To add the application to your desktop/menu:
1) Copy 3D_Plant_Scan.desktop to your applications directory:
- mkdir -p ~/.local/share/applications
- cp 3D_Plant_Scan.desktop ~/.local/share/applications/

2) Edit the Exec= line inside the .desktop file so it points to your Python and scan_ui.py, for example:
- Exec=/usr/bin/python3 /home/pi/3D_Plant_Scan/scan_ui.py

3) Make it executable (some desktops require this):
- chmod +x ~/.local/share/applications/3D_Plant_Scan.desktop

4) Refresh your desktop environment or log out/in.

---

## Updating Your Local Files (No Deletions)

Use the included update_repo.sh to pull the latest from GitHub and overlay files into your working directory without deleting extra local files:

Examples:
- sh update_repo.sh --repo https://github.com/Mr-Vale/3D_Plant_Scan.git --workdir ~/3D_Plant_Scan
- sh update_repo.sh --repo https://github.com/Mr-Vale/Network_Logger.git --workdir ~/Network_Logger
- sh update_repo.sh --repo https://github.com/Mr-Vale/RootBox-Software.git --workdir ~/RootBox

This will overwrite files that exist in the repo and add new ones, but it won’t remove unrelated local files.

Tip: If you edited update_repo.sh on Windows and see $'\r' errors, convert to Unix line endings:
- sed -i 's/\r$//' update_repo.sh

---

## Troubleshooting

- No cameras detected
  - Run: python3 cam_autodetect.py
  - Ensure the OS sees your cameras (lsusb, dmesg, or system tools)
  - Check USB power and cable quality
  - Confirm user permissions (e.g., plugdev, video groups)

- Scan won’t start
  - Check UI logs/messages
  - Ensure config.json is valid and at the repository root
  - Try headless: python3 scan_control.py to see console errors

- Turntable/motor issues
  - Verify wiring and power
  - Check turntable_control.py configuration and any required drivers
  - Run cleanup: python3 scan_control.py --cleanup

---

## License

This project is licensed — see [LICENSE](LICENSE) for details.

---

## Contributing

Issues and pull requests are welcome. Please include:
- Your environment (OS, Python version, hardware)
- Clear reproduction steps
- Logs or error messages (if applicable)
