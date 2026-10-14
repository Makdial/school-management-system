from django.db import transaction

from .models import AttendanceCorrection, StudentAttendance


@transaction.atomic
def bulk_upsert_attendance(school, session, attendance_date, section, records, user):
    """Create/update attendance for a list of ``{student, status, remark}``.

    * Idempotent per (student, session, date) thanks to the unique constraint.
    * Any status change is recorded in ``AttendanceCorrection`` for auditing.
    * Only students enrolled at ``school`` are accepted.
    """
    from students.models import Student

    ids = [str(r["student"]) for r in records]
    valid = {
        str(pk)
        for pk in Student.objects.filter(school=school, id__in=ids).values_list("id", flat=True)
    }
    saved = []
    for row in records:
        student_id = str(row["student"])
        if student_id not in valid:
            # Ignore cross school references rather than leaking their existence.
            continue
        status = row["status"]
        remark = row.get("remark", "") or ""
        existing = StudentAttendance.objects.filter(
            student_id=student_id, session=session, date=attendance_date
        ).first()
        if existing:
            if existing.status != status:
                AttendanceCorrection.objects.create(
                    attendance=existing,
                    previous_status=existing.status,
                    new_status=status,
                    reason=remark or "Attendance correction",
                    corrected_by=user,
                )
            existing.status = status
            if remark:
                existing.remark = remark
            existing.section = section or existing.section
            existing.recorded_by = user
            existing.save()
            saved.append(existing)
        else:
            saved.append(
                StudentAttendance.objects.create(
                    school=school,
                    student_id=student_id,
                    session=session,
                    section=section,
                    date=attendance_date,
                    status=status,
                    remark=remark,
                    recorded_by=user,
                )
            )
    return saved


def attendance_summary(school, session=None, section=None, student=None):
    """Return counts per status plus a percentage for the supplied filters."""
    qs = StudentAttendance.objects.filter(school=school)
    if session:
        qs = qs.filter(session_id=session)
    if section:
        qs = qs.filter(section_id=section)
    if student:
        qs = qs.filter(student_id=student)
    total = qs.count()
    present = qs.filter(status="PRESENT").count()
    late = qs.filter(status="LATE").count()
    absent = qs.filter(status="ABSENT").count()
    excused = qs.filter(status="EXCUSED").count()
    attended = present + late + excused
    percentage = round((attended / total) * 100, 2) if total else 0
    return {
        "total": total,
        "present": present,
        "late": late,
        "absent": absent,
        "excused": excused,
        "percentage": percentage,
    }
