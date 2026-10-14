from rest_framework import serializers

from .models import Room, TimetableEntry, TimetablePeriod


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class TimetablePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetablePeriod
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class TimetableEntrySerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True, default=None)
    room_name = serializers.CharField(source="room.name", read_only=True, default=None)
    section_name = serializers.CharField(source="section.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = TimetableEntry
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]

    def validate(self, attrs):
        def pick(field):
            return attrs.get(field) if attrs.get(field) is not None else getattr(self.instance, field, None)

        session = pick("session")
        section = pick("section")
        day = pick("day_of_week")
        period = pick("period")
        teacher = pick("teacher")
        room = pick("room")
        school = self.context["request"].user.school
        school_id = school.id if school else None

        if session and school_id and session.school_id != school_id:
            raise serializers.ValidationError("Session belongs to another school.")
        if section and session and section.grade_level.school_id != session.school_id:
            raise serializers.ValidationError("Section and session belong to different schools.")

        clashes = TimetableEntry.objects.filter(
            session=session, day_of_week=day, period=period
        )
        if self.instance:
            clashes = clashes.exclude(pk=self.instance.pk)

        if teacher and clashes.filter(teacher=teacher).exists():
            raise serializers.ValidationError("This teacher is already booked for that period.")
        if room and clashes.filter(room=room).exists():
            raise serializers.ValidationError("This room is already booked for that period.")
        if school_id and room and room.school_id != school_id:
            raise serializers.ValidationError("Room belongs to another school.")
        return attrs
