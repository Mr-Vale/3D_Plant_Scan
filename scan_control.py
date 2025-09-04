import logging
import time

from photo_control import PhotoController
from turntable_control import TurntableController

LOG_FILE = "scan_log.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)

class ScanController:
    def __init__(self, angle_per_photo=10, cameras=None, camera_map=None, delay=0.1):
        self.angle_per_photo = angle_per_photo
        self.num_steps = int(360 / angle_per_photo)
        self.cameras = cameras or ["Z", "Y", "Oblique"]
        self.camera_map = camera_map or {}
        self.delay = delay
        self.turntable = TurntableController()
        self.photo = PhotoController(self.cameras, camera_map=self.camera_map)
        self._stop = False
        logger.info("ScanController initialized with %.1f° per photo (%d steps) and cameras: %s.",
                    angle_per_photo, self.num_steps, self.cameras)

    def perform_scan(self, label="object"):
        self._stop = False
        logger.info("Starting scan for label: %s", label)
        for step in range(self.num_steps):
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

    def stop_scan(self):
        self._stop = True