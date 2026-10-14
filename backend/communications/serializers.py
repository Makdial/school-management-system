from rest_framework import serializers

from .models import Announcement, Message, Notification


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True, default=None)

    class Meta:
        model = Announcement
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "author"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "user"]


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    recipient_name = serializers.CharField(source="recipient.full_name", read_only=True)

    class Meta:
        model = Message
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "sender"]
