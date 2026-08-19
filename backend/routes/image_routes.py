import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import RoadReport, RoadImage, DamageDetection


# ==================================================
# YOLO
# ==================================================

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception:
    YOLO_AVAILABLE = False


# ==================================================
# ROUTER
# ==================================================

router = APIRouter(
    prefix="/images",
    tags=["Road Images"]
)


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

UPLOAD_DIR = PROJECT_ROOT / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==================================================
# YOLO MODEL
# ==================================================

MODEL_CANDIDATES = [
    PROJECT_ROOT / "ai" / "best.pt",
    PROJECT_ROOT / "ai" / "weights" / "best.pt",
    PROJECT_ROOT / "best.pt",
]

MODEL_PATH = next(
    (
        path
        for path in MODEL_CANDIDATES
        if path.exists()
    ),
    None
)


model = None

if YOLO_AVAILABLE and MODEL_PATH is not None:

    try:
        model = YOLO(str(MODEL_PATH))

    except Exception:
        model = None


# ==================================================
# SEVERITY CALCULATION
# ==================================================

def calculate_severity(
    detection_count: int,
    confidence: float
):

    if (
        detection_count >= 3
        or confidence >= 0.80
    ):

        return "high"

    elif (
        detection_count >= 2
        or confidence >= 0.60
    ):

        return "medium"

    else:

        return "low"


# ==================================================
# IMAGE UPLOAD + AI DETECTION
# ==================================================

@router.post("/upload/{report_id}")
def upload_image(
    report_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # ==================================================
    # CHECK REPORT
    # ==================================================

    report = (
        db.query(RoadReport)
        .filter(
            RoadReport.report_id == report_id
        )
        .first()
    )

    if not report:

        raise HTTPException(
            status_code=404,
            detail="Road report not found"
        )


    # ==================================================
    # CHECK FILE TYPE
    # ==================================================

    allowed_types = [
        "image/jpeg",
        "image/png",
        "image/jpg"
    ]

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG images are allowed"
        )


    # ==================================================
    # SAVE IMAGE
    # ==================================================

    safe_filename = os.path.basename(
        file.filename
    )

    file_path = UPLOAD_DIR / safe_filename

    with open(
        file_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    # ==================================================
    # SAVE IMAGE RECORD
    # ==================================================

    new_image = RoadImage(
        report_id=report_id,
        image_path=str(file_path)
    )

    db.add(new_image)
    db.commit()
    db.refresh(new_image)


    # ==================================================
    # AI DETECTION
    # ==================================================

    detections = []

    if model is not None:

        try:

            results = model.predict(
                source=str(file_path),
                conf=0.25,
                verbose=False
            )

            result = results[0]

            boxes = result.boxes
            names = result.names

            if (
                boxes is not None
                and len(boxes) > 0
            ):

                for i in range(len(boxes)):

                    class_id = int(
                        boxes.cls[i].item()
                    )

                    confidence = float(
                        boxes.conf[i].item()
                    )

                    if isinstance(
                        names,
                        dict
                    ):

                        damage_type = names.get(
                            class_id,
                            str(class_id)
                        )

                    else:

                        damage_type = names[
                            class_id
                        ]


                    # ----------------------------------
                    # SEVERITY
                    # ----------------------------------

                    severity = calculate_severity(
                        len(boxes),
                        confidence
                    )


                    # ----------------------------------
                    # SAVE DETECTION
                    # ----------------------------------

                    detection = DamageDetection(
                        report_id=report_id,
                        damage_type=damage_type,
                        confidence=confidence,
                        severity=severity
                    )

                    db.add(detection)


                    detections.append(
                        {
                            "damage_type": damage_type,
                            "confidence": round(
                                confidence,
                                4
                            ),
                            "severity": severity
                        }
                    )


                db.commit()


        except Exception as e:

            print(
                "AI detection failed:",
                str(e)
            )


    # ==================================================
    # RESPONSE
    # ==================================================

    return {

        "message":
            "Image uploaded successfully",

        "image_id":
            new_image.image_id,

        "report_id":
            report_id,

        "image_path":
            str(file_path),

        "ai_detected":
            len(detections) > 0,

        "detections":
            detections

    }
