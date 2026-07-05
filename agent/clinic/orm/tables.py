"""SQLAlchemy table definitions (replaces 001_schema.sql)."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    cancelled = "cancelled"
    completed = "completed"


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="Asia/Kolkata")
    phone: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    opening_time: Mapped[time] = mapped_column(Time, nullable=False)
    closing_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    doctors: Mapped[list[Doctor]] = relationship(back_populates="clinic")

    __table_args__ = (
        CheckConstraint("slot_minutes BETWEEN 10 AND 180", name="clinics_slot_minutes_check"),
    )


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    doctors: Mapped[list[Doctor]] = relationship(back_populates="specialty")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    specialty_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialties.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    qualifications: Mapped[str | None] = mapped_column(Text)
    languages: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    clinic: Mapped[Clinic] = relationship(back_populates="doctors")
    specialty: Mapped[Specialty] = relationship(back_populates="doctors")
    schedules: Mapped[list[DoctorSchedule]] = relationship(back_populates="doctor", cascade="all, delete-orphan")
    blocked_periods: Mapped[list[BlockedPeriod]] = relationship(back_populates="doctor", cascade="all, delete-orphan")
    appointments: Mapped[list[Appointment]] = relationship(back_populates="doctor")

    __table_args__ = (UniqueConstraint("clinic_id", "name", name="doctors_clinic_id_name_key"),)


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    doctor: Mapped[Doctor] = relationship(back_populates="schedules")

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="doctor_schedules_weekday_check"),
        CheckConstraint("start_time < end_time", name="doctor_schedules_time_check"),
        UniqueConstraint("doctor_id", "weekday", "start_time", name="doctor_schedules_doctor_id_weekday_start_time_key"),
    )


class BlockedPeriod(Base):
    __tablename__ = "blocked_periods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

    doctor: Mapped[Doctor] = relationship(back_populates="blocked_periods")

    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="blocked_periods_time_check"),
        Index("blocked_periods_doctor_idx", "doctor_id", "starts_at"),
    )


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointments: Mapped[list[Appointment]] = relationship(back_populates="patient")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_reference: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status", native_enum=True),
        nullable=False,
        default=AppointmentStatus.scheduled,
    )
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    doctor: Mapped[Doctor] = relationship(back_populates="appointments")
    patient: Mapped[Patient] = relationship(back_populates="appointments")

    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="appointments_time_check"),
        CheckConstraint("language IN ('en', 'hi', 'te')", name="appointments_language_check"),
        Index("appointments_patient_idx", "patient_id", starts_at.desc()),
        Index(
            "one_active_appointment_per_doctor_slot",
            "doctor_id",
            "starts_at",
            unique=True,
            postgresql_where=text("status = 'scheduled'"),
        ),
    )
