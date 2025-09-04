import logging
import os
import subprocess

logger = logging.getLogger(__name__)

class PhotoController:
    def __init__(self, axes, camera_map=None):
        self.axes = axes
        logger.info("PhotoController initialized for axes: %s", axes)
        # Use supplied camera_map or detect
        self.camera_map = camera_map if camera_map else self.detect_cameras()

    def detect_cameras(self):
        try:
            result = subprocess.run(
                ["gphoto2", "--auto-detect"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            lines = result.stdout.splitlines()
            camera_ports = [line for line in lines if "usb:" in line]
            camera_map = {}
            for i, axis in enumerate(self.axes):
                if i < len(camera_ports):
                    port = camera_ports[i].split()[-1]
                    camera_map[axis] = port
                else:
                    logger.warning("No camera found for axis %s", axis)
            logger.info("Camera map: %s", camera_map)
            return camera_map
        except Exception as e:
            logger.error("Failed to detect cameras: %s", str(e))
            return {}

    def capture(self, axis, filename=None):
        port = self.camera_map.get(axis)
        if not port:
            raise RuntimeError(f"No camera mapped for axis {axis}")

        folder = os.path.dirname(filename)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        cmd = [
            "gphoto2",
            f"--port={port}",
            "--capture-image-and-download",
            f"--filename={filename}",
            "--force-overwrite"
        ]
        logger.info("Capturing photo on axis %s, port %s, filename %s", axis, port, filename)
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                logger.error("gphoto2 error: %s", result.stderr)
                raise RuntimeError(f"gphoto2 capture failed for axis {axis}: {result.stderr}")
            logger.info("Photo saved: %s", filename)
        except Exception as e:
            logger.error("Capture failed for axis %s: %s", axis, str(e))
            raise

    def list_cameras(self):
        return self.camera_map