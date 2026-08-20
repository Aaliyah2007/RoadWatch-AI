# ============================================================
# YOLO IMPORT
# ============================================================

try:
    import os

    # Force headless OpenCV for Railway/Linux server
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

    import cv2
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
    YOLO_IMPORT_ERROR = ""

except Exception as e:
    YOLO_AVAILABLE = False
    YOLO_IMPORT_ERROR = str(e)
