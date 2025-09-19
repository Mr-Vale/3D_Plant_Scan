import subprocess
import json
import re
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
AXES = ["Z", "Y", "Oblique"]

def detect_cameras():
    try:
        result = subprocess.run(['gphoto2', '--auto-detect'], capture_output=True, text=True, check=True)
        cameras = []
        lines = result.stdout.strip().splitlines()
        for line in lines[2:]:  # skip header
            line = line.strip()
            if not line:
                continue
            parts = re.split(r'\s{2,}', line)
            if len(parts) == 2:
                model, port = parts
                cameras.append({"model": model, "port": port})
        return cameras
    except Exception as e:
        print(f"Error detecting cameras: {e}")
        return []

def update_config_with_cameras(cameras):
    config = {
        "scan_label": "my_plant_scan",
        "angle_per_photo": 10,
        "axes": {},
        "cameras": [],
        "step_delay": 0.1
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"Error reading config.json: {e}")

    # Build a list of detected ports
    detected_ports = [cam["port"] for cam in cameras]

    # Assign detected ports to axes in order (Z, Y, Oblique)
    axes = {}
    cameras_list = []
    for idx, cam in enumerate(cameras):
        if idx < len(AXES):
            axis = AXES[idx]
            axes[axis] = cam["port"]
            cameras_list.append({"axis": axis, "port": cam["port"]})

    config["axes"] = axes
    config["cameras"] = cameras_list

    angle = config.get("angle_per_photo", 10)
    num_cams = len(cameras_list)
    config["photos_per_camera"] = 360 // angle if angle > 0 else 0
    config["total_photos"] = config["photos_per_camera"] * num_cams

    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config.json: {e}")

def main():
    cameras = detect_cameras()
    update_config_with_cameras(cameras)

if __name__ == "__main__":
    main()