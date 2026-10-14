def detect_conflicts(entries):
    """Return a list of teacher/room double bookings within a queryset."""
    seen = {}
    conflicts = []
    for entry in entries:
        if entry.is_break if hasattr(entry, "is_break") else False:
            continue
        key_base = (entry.session_id, entry.day_of_week, entry.period_id)
        if entry.teacher_id:
            key = ("teacher", entry.teacher_id, key_base)
            if key in seen:
                conflicts.append(
                    {
                        "type": "teacher",
                        "teacher": entry.teacher_id,
                        "entry": str(entry.id),
                        "conflicts_with": str(seen[key].id),
                    }
                )
            else:
                seen[key] = entry
        if entry.room_id:
            key = ("room", entry.room_id, key_base)
            if key in seen:
                conflicts.append(
                    {
                        "type": "room",
                        "room": entry.room_id,
                        "entry": str(entry.id),
                        "conflicts_with": str(seen[key].id),
                    }
                )
            else:
                seen[key] = entry
    return conflicts
