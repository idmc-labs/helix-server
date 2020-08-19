from rest_framework import serializers

from apps.crisis.models import Crisis


class CrisisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crisis
        fields = '__all__'
