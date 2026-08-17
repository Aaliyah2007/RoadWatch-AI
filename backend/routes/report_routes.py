from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    RoadReport,
    User,
    ReportStatusHistory,
    DamageDetection
)
from ..schemas import ReportCreate


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

            # ==============================================
            # AI INFORMATION
            # ==============================================

            "ai_detected": len(detection_list) > 0,
            "detections": detection_list
        })

    return {
        "total_reports": len(report_list),
        "reports": report_list
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


    # ------------------------------------------------------
    # VERIFY OFFICIAL USER
    # ------------------------------------------------------

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


    # ------------------------------------------------------
    # VALIDATE STATUS
    # ------------------------------------------------------

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


    # ------------------------------------------------------
    # STORE OLD STATUS
    # ------------------------------------------------------

    old_status = report.status


    # ------------------------------------------------------
    # UPDATE CURRENT STATUS
    # ------------------------------------------------------

    report.status = status


    # ------------------------------------------------------
    # CREATE STATUS HISTORY RECORD
    # ------------------------------------------------------

    history = ReportStatusHistory(
        report_id=report_id,
        old_status=old_status,
        new_status=status,
        changed_by=official_user_id
    )

    db.add(history)


    # ------------------------------------------------------
    # SAVE BOTH CHANGES
    # ------------------------------------------------------

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
