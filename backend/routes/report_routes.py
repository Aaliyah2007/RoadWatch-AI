from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    RoadReport,
    User,
    ReportStatusHistory,
    DamageDetection,
    ReportMessage
)
from schemas import ReportCreate


router = APIRouter(
    prefix="/reports",
    tags=["Road Reports"]
)


# ==========================================================
# CREATE ROAD REPORT
# ==========================================================

@router.post("/")
def create_report(
    report_data: ReportCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_report = RoadReport(
        user_id=user_id,
        description=report_data.description,
        latitude=report_data.latitude,
        longitude=report_data.longitude,
        address=report_data.address
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return {
        "message": "Road report submitted successfully",
        "report_id": new_report.report_id,
        "status": new_report.status
    }


# ==========================================================
# GET ALL REPORTS + AI DETECTIONS
# ==========================================================

@router.get("/")
def get_reports(
    db: Session = Depends(get_db)
):
    reports = (
        db.query(RoadReport)
        .order_by(RoadReport.created_at.desc())
        .all()
    )

    report_list = []

    for report in reports:

        detections = (
            db.query(DamageDetection)
            .filter(
                DamageDetection.report_id == report.report_id
            )
            .order_by(
                DamageDetection.detected_at.asc()
            )
            .all()
        )

        detection_list = []

        for detection in detections:

            detection_list.append({
                "detection_id": detection.detection_id,
                "damage_type": detection.damage_type,
                "confidence": (
                    float(detection.confidence)
                    if detection.confidence is not None
                    else None
                ),
                "severity": detection.severity,
                "detected_at": detection.detected_at
            })

        # ======================================================
        # CALCULATE OVERALL SEVERITY + RCI
        # ======================================================

        if detection_list:

            max_confidence = max(
                d["confidence"] or 0
                for d in detection_list
            )

            if (
                len(detection_list) >= 3
                or max_confidence >= 0.80
            ):
                overall_severity = "High"
                rci_score = 3

            elif (
                len(detection_list) >= 2
                or max_confidence >= 0.60
            ):
                overall_severity = "Medium"
                rci_score = 2

            else:
                overall_severity = "Low"
                rci_score = 1

        else:

            overall_severity = None
            rci_score = None

        report_list.append({
            "report_id": report.report_id,
            "user_id": report.user_id,
            "description": report.description,
            "latitude": (
                float(report.latitude)
                if report.latitude is not None
                else None
            ),
            "longitude": (
                float(report.longitude)
                if report.longitude is not None
                else None
            ),
            "address": report.address,
            "status": report.status,
            "created_at": report.created_at,
            "updated_at": report.updated_at,

            # AI INFORMATION
            "ai_detected": len(detection_list) > 0,
            "detections": detection_list,
            "overall_severity": overall_severity,
            "rci_score": rci_score
        })

    return {
        "total_reports": len(report_list),
        "reports": report_list
    }


# ==========================================================
# SAVE AI DETECTIONS FOR A REPORT
# ==========================================================

@router.post("/{report_id}/detections")
def save_detections(
    report_id: int,
    data: dict,
    db: Session = Depends(get_db)
):

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

    # Remove previous detections for this report
    db.query(DamageDetection).filter(
        DamageDetection.report_id == report_id
    ).delete()

    detections = data.get("detections", [])

    saved_detections = []

    for detection in detections:

        damage_detection = DamageDetection(
            report_id=report_id,
            damage_type=detection.get(
                "damage_type",
                detection.get("class", "Unknown")
            ),
            confidence=detection.get("confidence"),
            severity=detection.get(
                "severity",
                "low"
            ).lower()
        )

        db.add(damage_detection)
        saved_detections.append(damage_detection)

    db.commit()

    return {
        "message": "AI detections saved successfully",
        "report_id": report_id,
        "detection_count": len(saved_detections)
    }


# ==========================================================
# UPDATE REPORT STATUS + SAVE HISTORY
# ==========================================================

@router.put("/{report_id}/status")
def update_report_status(
    report_id: int,
    status: str,
    official_user_id: int,
    db: Session = Depends(get_db)
):

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

    # VERIFY OFFICIAL USER

    official = (
        db.query(User)
        .filter(
            User.user_id == official_user_id,
            User.role == "official"
        )
        .first()
    )

    if not official:
        raise HTTPException(
            status_code=403,
            detail="Only an official can update report status"
        )

    # VALIDATE STATUS

    allowed_statuses = [
        "submitted",
        "under_review",
        "in_progress",
        "resolved",
        "rejected"
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    # STORE OLD STATUS

    old_status = report.status

    # UPDATE CURRENT STATUS

    report.status = status

    # CREATE STATUS HISTORY RECORD

    history = ReportStatusHistory(
        report_id=report_id,
        old_status=old_status,
        new_status=status,
        changed_by=official_user_id
    )

    db.add(history)

    # SAVE BOTH CHANGES

    db.commit()

    db.refresh(report)
    db.refresh(history)

    return {
        "message": "Report status updated successfully",
        "report_id": report.report_id,
        "old_status": old_status,
        "new_status": report.status,
        "changed_by": official_user_id,
        "history_id": history.history_id
    }


# ==========================================================
# GET STATUS HISTORY FOR A REPORT
# ==========================================================

@router.get("/{report_id}/history")
def get_report_history(
    report_id: int,
    db: Session = Depends(get_db)
):

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

    history = (
        db.query(ReportStatusHistory)
        .filter(
            ReportStatusHistory.report_id == report_id
        )
        .order_by(
            ReportStatusHistory.changed_at.asc()
        )
        .all()
    )

    return {
        "report_id": report_id,
        "history": history
    }


# ==========================================================
# GET MESSAGES FOR A REPORT
# ==========================================================

@router.get("/{report_id}/messages")
def get_report_messages(
    report_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # FIND REPORT
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # FIND REQUESTING USER
    # ------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.user_id == user_id
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ------------------------------------------------------
    # ACCESS CONTROL
    # Citizen must own the report.
    # Official can access any report.
    # ------------------------------------------------------

    if (
        user.role != "official"
        and report.user_id != user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view these messages"
        )

    # ------------------------------------------------------
    # GET MESSAGES
    # ------------------------------------------------------

    messages = (
        db.query(ReportMessage)
        .filter(
            ReportMessage.report_id == report_id
        )
        .order_by(
            ReportMessage.created_at.asc()
        )
        .all()
    )

    return {
        "report_id": report_id,
        "messages": [
            {
                "message_id": message.message_id,
                "report_id": message.report_id,
                "sender_id": message.sender_id,
                "sender_role": message.sender_role,
                "message": message.message,
                "created_at": message.created_at
            }
            for message in messages
        ]
    }


# ==========================================================
# SEND MESSAGE
# ==========================================================

@router.post("/{report_id}/messages")
def send_report_message(
    report_id: int,
    user_id: int,
    data: dict,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # FIND REPORT
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # FIND SENDER
    # ------------------------------------------------------

    sender = (
        db.query(User)
        .filter(
            User.user_id == user_id
        )
        .first()
    )

    if not sender:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ------------------------------------------------------
    # ACCESS CONTROL
    # ------------------------------------------------------

    if (
        sender.role != "official"
        and report.user_id != user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to send messages for this report"
        )

    # ------------------------------------------------------
    # VALIDATE MESSAGE
    # ------------------------------------------------------

    message_text = data.get("message")

    if not message_text or not message_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    message_text = message_text.strip()

    # ------------------------------------------------------
    # CREATE MESSAGE
    # ------------------------------------------------------

    new_message = ReportMessage(
        report_id=report_id,
        sender_id=user_id,
        sender_role=sender.role,
        message=message_text
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "message": "Message sent successfully",
        "message_id": new_message.message_id,
        "report_id": new_message.report_id,
        "sender_id": new_message.sender_id,
        "sender_role": new_message.sender_role,
        "message_text": new_message.message,
        "created_at": new_message.created_at
    }