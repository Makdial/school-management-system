from rest_framework import serializers


class MessageSerializer(serializers.Serializer):
    detail = __import__("rest_framework").serializers.CharField()
