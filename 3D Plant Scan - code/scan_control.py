import logging
import time
import json
import os
import subprocess

from photo_control import PhotoController
from turntable_control import TurntableController

LOG_FILE = "scan_log.txt"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
AUTODETECT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cam_autodetect.py')
AXES = ["Z", "Y", "Oblique"]

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)

def run_camera_autodetect():
    try:
        subprocess.run(["python3", AUTODETECT_SCRIPT], check=True)
    except Exception as e:
        logger.error("Error running camera autodetect: %s", str(e))

def load_camera_config():
    if not os.path.exists(CONFIG_PATH):
        return AXES, {}
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    axes_config = config.get("axes", {})
    # Only use axes assigned and not set to "None"
    cameras = [axis for axis in AXES if axes_config.get(axis, "None") != "None"]
    camera_map = {axis: axes_config.get(axis) for axis in cameras}
    return cameras, camera_map

class ScanController:
    def __init__(self, angle_per_photo=10, cameras=None, camera_map=None, delay=0.1, photo_mode="immediate"):
        self.angle_per_photo = angle_per_photo
        self.num_steps = int(360 / angle_per_photo)
        # If not provided, load from config
        if cameras is None or camera_map is None:
            cameras, camera_map = load_camera_config()
        self.cameras = cameras
        self.camera_map = camera_map
        self.delay = delay
        self.turntable = TurntableController()
        self.photo = PhotoController(self.cameras, camera_map=self.camera_map, mode=photo_mode)
        self._stop = False
        logger.info("ScanController initialized with %.1f° per photo (%d steps) and cameras: %s. Photo mode: %s",
                    angle_per_photo, self.num_steps, self.cameras, photo_mode)

    def refresh_cameras(self):
        """Call autodetect and reload camera assignments from config.json."""
        run_camera_autodetect()
        cameras, camera_map = load_camera_config()
        self.cameras = cameras
        self.camera_map = camera_map
        self.photo = PhotoController(self.cameras, camera_map=self.camera_map)
        logger.info("Camera assignments refreshed: %s", self.cameras)

    def perform_scan(self, label="object"):
        self._stop = False
        logger.info("Starting scan for label: %s", label)

        # Take initial photo at 0° before any movement
        initial_angle = 0
        for axis in self.cameras:
            try:
                filename = f"{label}/" \
                           f"{axis}/camera{self.cameras.index(axis)+1} - {axis} - angle{int(initial_angle):03d}.jpg"
                self.photo.capture(axis, filename)
                logger.info("Captured initial photo for axis %s at angle %.1f°", axis, initial_angle)
            except Exception as e:
                logger.error("Failed to capture initial photo on axis %s at angle %.1f: %s", axis, initial_angle, str(e))
        time.sleep(self.delay)

        # Now start actual scan loop (rotation + photo)
        for step in range(1, self.num_steps):
            if self._stop:
                logger.info("Scan stopped by user.")
                break
            angle = step * self.angle_per_photo
            logger.info("Rotating to angle %.1f° (step %d)", angle, step)
            self.turntable.move_degrees(self.angle_per_photo)
            for axis in self.cameras:
                try:
                    filename = f"{label}/" \
                               f"{axis}/camera{self.cameras.index(axis)+1} - {axis} - angle{int(angle):03d}.jpg"
                    self.photo.capture(axis, filename)
                    logger.info("Captured photo for axis %s at angle %.1f° (step %d)", axis, angle, step)
                except Exception as e:
                    logger.error("Failed to capture photo on axis %s at angle %.1f: %s", axis, angle, str(e))
            time.sleep(self.delay)

        logger.info("Scan complete.")
        
        # Always reset turntable to 0° at the end
        logger.info("Resetting turntable to 0° (starting position).")
        self.turntable.reset_position()
        logger.info("Turntable reset complete.")

        # If in sdcard mode, download all photos from the cameras to the Pi
        if getattr(self.photo, "mode", "immediate") == "sdcard":
            logger.info("Downloading all images from camera SD cards.")
            try:
                self.photo.download_all(label=label)
                logger.info("All images downloaded from SD cards.")
            except Exception as e:
                logger.error("Failed to download all images from SD cards: %s", str(e))

    def stop_scan(self):
        self._stop = True

if __name__ == "__main__":
    # Load config for scan name & angle
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        label = config.get("scan_label", "object")
        angle = float(config.get("angle_per_photo", 10))
        step_delay = float(config.get("step_delay", 0.1))
        photo_mode = config.get("photo_mode", "immediate")
    else:
        label = "object"
        angle = 10
        step_delay = 0.1
        photo_mode = "immediate"

    # Load camera mapping
    cameras, camera_map = load_camera_config()

    # Run scan!
    ScanController(
        angle_per_photo=angle,
        cameras=cameras,
        camera_map=camera_map,
        delay=step_delay,
        photo_mode=photo_mode
    ).perform_scan(label=label)