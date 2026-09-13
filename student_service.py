"""
services/student_service.py
Business logic for managing student accounts and profiles, kept separate
from the Flask route layer so it can be reused by both the HTML views and
the JSON API.
"""

import logging

from werkzeug.security import generate_password_hash

from ai_engine import embedding_manager
from database.db import db
from models.attendance import Attendance, FaceData
from models.student import Student
from models.user import User
from utils.validators import (
    ValidationError,
    validate_email,
    validate_enrollment_number,
    validate_phone,
    validate_semester,
)

logger = logging.getLogger("smart_attendance.services")


def create_student(data: dict) -> Student:
    """Create a User(role=student) + Student profile in one transaction."""
    full_name = (data.get("full_name") or "").strip()
    if not full_name:
        raise ValidationError("Full name is required.")

    email = validate_email(data.get("email"))
    enrollment_number = validate_enrollment_number(data.get("enrollment_number"))
    department = (data.get("department") or "").strip()

    if not department:
        raise ValidationError("Department is required.")

    semester = validate_semester(data.get("semester"))
    division = (data.get("division") or "").strip().upper()

    if not division:
        raise ValidationError("Division is required.")

    phone_number = validate_phone(data.get("phone_number"))

    if User.query.filter_by(email=email).first():
        raise ValidationError(f"A user with email {email} already exists.")

    if Student.query.filter_by(
        enrollment_number=enrollment_number
    ).first():
        raise ValidationError(
            f"A student with enrollment number {enrollment_number} already exists."
        )

    raw_password = data.get("password") or enrollment_number

    user = User(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(raw_password),
        role="student",
    )

    db.session.add(user)
    db.session.flush()

    student = Student(
        user_id=user.id,
        enrollment_number=enrollment_number,
        department=department,
        semester=semester,
        division=division,
        phone_number=phone_number,
    )

    db.session.add(student)
    db.session.commit()

    logger.info(
        "Created student %s (%s)",
        enrollment_number,
        email,
    )

    return student


def update_student(student_id: int, data: dict) -> Student:
    student = Student.query.get(student_id)

    if not student:
        raise ValidationError("Student not found.")

    if "full_name" in data and data["full_name"].strip():
        student.user.full_name = data["full_name"].strip()

    if "email" in data and data["email"].strip():
        new_email = validate_email(data["email"])

        existing = User.query.filter(
            User.email == new_email,
            User.id != student.user_id,
        ).first()

        if existing:
            raise ValidationError(
                f"A user with email {new_email} already exists."
            )

        student.user.email = new_email

    if "department" in data and data["department"].strip():
        student.department = data["department"].strip()

    if "semester" in data and data["semester"] not in (None, ""):
        student.semester = validate_semester(data["semester"])

    if "division" in data and data["division"].strip():
        student.division = data["division"].strip().upper()

    if "phone_number" in data:
        student.phone_number = validate_phone(
            data.get("phone_number")
        )

    db.session.commit()

    logger.info(
        "Updated student id=%s",
        student_id,
    )

    return student


def delete_student(student_id: int) -> None:
    """
    Permanently delete a student and all dependent face/attendance data.

    Deletion order is important because the database has foreign-key
    constraints:

        face_embeddings -> face_data -> student
        attendance      -> student
    """

    student = Student.query.get(student_id)

    if not student:
        raise ValidationError("Student not found.")

    user = student.user

    try:
        # ---------------------------------------------------------
        # 1. Delete face embeddings first
        # ---------------------------------------------------------
        #
        # face_embeddings.face_data_id references face_data.id.
        # Therefore face_embeddings MUST be deleted before face_data.
        #
        embedding_manager.delete_student_embeddings(student_id)

        # ---------------------------------------------------------
        # 2. Explicitly remove any remaining FaceData records
        # ---------------------------------------------------------
        #
        # This handles databases where the embedding manager removes
        # files but does not completely remove the database records.
        #
        face_data_records = FaceData.query.filter_by(
            student_id=student_id
        ).all()

        for face_data in face_data_records:
            # Delete any embeddings that still reference this face_data.
            #
            # We use the relationship/query dynamically through the
            # FaceData ID so this remains safe with the existing schema.
            db.session.execute(
                db.text(
                    "DELETE FROM face_embeddings "
                    "WHERE face_data_id = :face_data_id"
                ),
                {
                    "face_data_id": face_data.id
                },
            )

        # Now FaceData can safely be deleted.
        for face_data in face_data_records:
            db.session.delete(face_data)

        # ---------------------------------------------------------
        # 3. Delete attendance records
        # ---------------------------------------------------------
        #
        # Attendance references the student. Remove those records
        # before deleting the student.
        #
        attendance_records = Attendance.query.filter_by(
            student_id=student_id
        ).all()

        for attendance in attendance_records:
            db.session.delete(attendance)

        # ---------------------------------------------------------
        # 4. Delete the Student record
        # ---------------------------------------------------------
        db.session.delete(student)

        # ---------------------------------------------------------
        # 5. Delete the associated User account
        # ---------------------------------------------------------
        if user:
            db.session.delete(user)

        # ---------------------------------------------------------
        # 6. Commit everything as one transaction
        # ---------------------------------------------------------
        db.session.commit()

        logger.info(
            "Deleted student id=%s and all dependent data",
            student_id,
        )

    except Exception:
        db.session.rollback()

        logger.exception(
            "Failed to delete student id=%s",
            student_id,
        )

        raise


def search_students(
    query: str = "",
    department: str = "",
    semester=None,
    division: str = "",
    page: int = 1,
    per_page: int = 20,
):
    q = Student.query.join(User)

    if query:
        like = f"%{query.strip()}%"

        q = q.filter(
            db.or_(
                User.full_name.ilike(like),
                Student.enrollment_number.ilike(like),
                User.email.ilike(like),
            )
        )

    if department:
        q = q.filter(Student.department == department)

    if semester:
        q = q.filter(Student.semester == semester)

    if division:
        q = q.filter(Student.division == division)

    q = q.order_by(User.full_name.asc())

    return q.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )


def get_student_attendance_summary(student_id: int):
    """Overall + subject-wise attendance percentage for a student."""

    records = Attendance.query.filter_by(
        student_id=student_id
    ).all()

    total = len(records)

    present = sum(
        1
        for r in records
        if r.status in ("Present", "Manual Present")
    )

    overall_percentage = (
        round((present / total) * 100, 1)
        if total
        else 0.0
    )

    subject_stats = {}

    for record in records:
        lecture = record.lecture

        if not lecture or not lecture.subject:
            continue

        key = lecture.subject.subject_code

        stats = subject_stats.setdefault(
            key,
            {
                "subject_name": lecture.subject.subject_name,
                "total": 0,
                "present": 0,
            },
        )

        stats["total"] += 1

        if record.status in ("Present", "Manual Present"):
            stats["present"] += 1

    for stats in subject_stats.values():
        stats["percentage"] = (
            round(
                (stats["present"] / stats["total"]) * 100,
                1,
            )
            if stats["total"]
            else 0.0
        )

    return {
        "total_lectures": total,
        "present_count": present,
        "overall_percentage": overall_percentage,
        "subject_wise": subject_stats,
    }