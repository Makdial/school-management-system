from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Exam(SchoolScopedModel):
    EXAM_TYPES = [
        ("CONTINUOUS", "Continuous Assessment"),
        ("MIDTERM", "Mid Term"),
        ("ENDTERM", "End of Term"),
        ("MOCK", "Mock"),
        ("FINAL", "Final"),
    ]

    name = models.CharField(max_length=160)
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="exams")
    term = models.ForeignKey("schools.Term", null=True, blank=True, on_delete=models.SET_NULL, related_name="exams")
    exam_type = models.CharField(max_length=16, choices=EXAM_TYPES, default="ENDTERM")
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]
        unique_together = [("school", "session", "name")]

    def __str__(self):
        return self.name


class ExamSubject(SchoolScopedModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="subjects")
    class_subject = models.ForeignKey(
        "academics.ClassSubject", on_delete=models.CASCADE, related_name="exam_subjects"
    )
    exam_date = models.DateField(null=True, blank=True)
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    pass_marks = models.DecimalField(max_digits=6, decimal_places=2, default=40)
    room = models.ForeignKey(
        "timetable.Room", null=True, blank=True, on_delete=models.SET_NULL, related_name="exam_subjects"
    )

    class Meta:
        unique_together = [("exam", "class_subject")]
        ordering = ["exam_date", "class_subject__subject__name"]

    def __str__(self):
        return f"{self.exam.name} - {self.class_subject.subject.name}"

    def clean(self):
        if self.pass_marks and self.max_marks and self.pass_marks > self.max_marks:
            from django.core.exceptions import ValidationError

            raise ValidationError({"pass_marks": "Pass marks cannot exceed max marks."})


class StudentMark(BaseModel):
    exam_subject = models.ForeignKey(ExamSubject, on_delete=models.CASCADE, related_name="marks")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="marks")
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_absent = models.BooleanField(default=False)
    entered_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("exam_subject", "student")]
        ordering = ["student__last_name"]

    def __str__(self):
        return f"{self.student} {self.exam_subject}: {self.marks_obtained}"

    @property
    def percentage(self):
        max_marks = self.exam_subject.max_marks or 1
        return round(float(self.marks_obtained) / float(max_marks) * 100, 2)

    @property
    def grade(self):
        from examinations.services import resolve_grade

        exam = self.exam_subject.exam
        scale = exam.school and self.exam_subject.exam.school.grading_scales.filter(
            is_default=True
        ).first()
        if not scale:
            scale = exam.school.grading_scales.first() if exam.school else None
        return resolve_grade(scale, self.percentage) if scale else ""


class ReportCard(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="report_cards")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="report_cards")
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_max = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    average = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    grade = models.CharField(max_length=8, blank=True)
    position = models.PositiveIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = [("student", "exam")]
        ordering = ["position"]

    def __str__(self):
        return f"Report {self.student} / {self.exam}"
