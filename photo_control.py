import logging
import os
import subprocess
import glob
import shutil

logger = logging.getLogger(__name__)

class PhotoController:
    def __init__(self, axes, camera_map=None, mode="immediate"):
        """
        mode: "immediate" - capture and download after each shot (default)
              "sdcard"    - just trigger shutter during scan, download all at end
        """
        self.axes = axes
        logger.info("PhotoController initialized for axes: %s", axes)
        self.camera_map = camera_map if camera_map else self.detect_cameras()
        self.mode = mode  # "immediate" or "sdcard"
        if self.mode == "sdcard":
            self._set_camera_sdcard()

    def _set_camera_sdcard(self):
        for axis, port in self.camera_map.items():
            try:
                subprocess.run(
                    ["gphoto2", f"--port={port}", "--set-config", "capturetarget=1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                logger.info("Set camera on axis %s (%s) to store on SD card.", axis, port)
            except Exception as e:
                logger.warning("Could not set SD storage for axis %s (%s): %s", axis, port, str(e))

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
        if not port or port == "None":
            raise RuntimeError(f"No camera mapped for axis {axis}")

        # Fake Camera support
        if port == "Fake Camera":
            folder = os.path.dirname(filename)
            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
            logger.info("[FAKE CAMERA] Simulating photo capture for axis %s at %s", axis, filename)
            with open(filename, "w") as f:
                f.write(f"FAKE PHOTO for axis {axis}\n")
            return

        folder = os.path.dirname(filename)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        if self.mode == "sdcard":
            cmd = [
                "gphoto2",
                f"--port={port}",
                "--capture-image"
            ]
            logger.info("Triggering photo on axis %s, port %s (store on SD card)", axis, port)
        else:
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
            if self.mode != "sdcard":
                logger.info("Photo saved: %s", filename)
        except Exception as e:
            logger.error("Capture failed for axis %s: %s", axis, str(e))
            raise

    def download_all(self, label="scan", angle_per_photo=90):
        """
        Download all images from the SD card of each camera after the scan, rename them based on scan order,
        and delete photos from the camera after transfer.
        """
        for axis, port in self.camera_map.items():
            temp_dir = f"/tmp/{label}_{axis}"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)

            # 1. Download all files from camera to temp folder
            cmd = [
                "gphoto2",
                f"--port={port}",
                "--get-all-files",
                f"--filename={temp_dir}/%f"
            ]
            logger.info("Downloading all files from camera on axis %s (%s) to %s", axis, port, temp_dir)
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    logger.error("gphoto2 download error: %s", result.stderr)
                    raise RuntimeError(f"gphoto2 download failed for axis {axis}: {result.stderr}")
            except Exception as e:
                logger.error("Download failed for axis %s: %s", axis, str(e))
                raise

            # 2. Sort images by filename (usually matches capture order)
            images = sorted(glob.glob(f"{temp_dir}/*"))

            # 3. Rename and move images to the final output directory
            output_dir = os.path.join(label, axis)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            for idx, img_path in enumerate(images):
                angle = int(idx * angle_per_photo)
                outname = f"axis {axis} - angle{angle:03d}.jpg"
                outpath = os.path.join(output_dir, outname)
                shutil.move(img_path, outpath)
                logger.info("Moved and renamed: %s -> %s", img_path, outpath)

            # 4. Delete all images on the camera
            del_cmd = [
                "gphoto2",
                f"--port={port}",
                "--recurse",
                "--delete-all-files"
            ]
            logger.info("Deleting all files from camera on axis %s (%s)", axis, port)
            try:
                del_result = subprocess.run(
                    del_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                logger.info("Delete output: %s", del_result.stdout)
                if del_result.stderr:
                    logger.warning("Delete stderr: %s", del_result.stderr)
            except Exception as e:
                logger.error("Failed to delete files from camera on axis %s: %s", axis, str(e))

            # 5. Remove temporary directory
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass  # Directory not empty or already deleted

    def list_cameras(self):
        return self.camera_map