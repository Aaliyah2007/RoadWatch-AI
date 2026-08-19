from sqlalchemy import Column, Integer, String, Text, DECIMAL, Enum, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("citizen", "official"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    reports = relationship("RoadReport", back_populates="user")
    status_changes = relationship("ReportStatusHistory", back_populates="changed_by_user")


class RoadReport(Base):
    __tablename__ = "road_reports"

    report_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    description = Column(Text)
    latitude = Column(DECIMAL(10, 7))
    longitude = Column(DECIMAL(10, 7))
    address = Column(String(255))
    status = Column(
        Enum(
            "submitted",
            "under_review",
            "in_progress",
            "resolved",
            "rejected"
        ),
        default="submitted"
    )
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    user = relationship("User", back_populates="reports")
    images = relationship(
        "RoadImage",
        back_populates="report",
        cascade="all, delete-orphan"
    )
    detections = relationship(
        "DamageDetection",
        back_populates="report",
        cascade="all, delete-orphan"
    )
    status_history = relationship(
        "ReportStatusHistory",
        back_populates="report",
        cascade="all, delete-orphan"
    )


class RoadImage(Base):
    __tablename__ = "road_images"

    image_id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer,
        ForeignKey("road_reports.report_id", ondelete="CASCADE"),
        nullable=False
    )
    image_path = Column(String(500), nullable=False)
    uploaded_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    report = relationship("RoadReport", back_populates="images")


class DamageDetection(Base):
    __tablename__ = "damage_detections"

    detection_id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer,
        ForeignKey("road_reports.report_id", ondelete="CASCADE"),
        nullable=False
    )
    damage_type = Column(String(100))
    confidence = Column(DECIMAL(5, 2))
    severity = Column(Enum("low", "medium", "high"))
    detected_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    report = relationship("RoadReport", back_populates="detections")


class ReportStatusHistory(Base):
    __tablename__ = "report_status_history"

    history_id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer,
        ForeignKey("road_reports.report_id", ondelete="CASCADE"),
        nullable=False
    )
    old_status = Column(String(50))
    new_status = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    changed_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    report = relationship("RoadReport", back_populates="status_history")
    changed_by_user = relationship(
        "User",
        back_populates="status_changes"
    )
