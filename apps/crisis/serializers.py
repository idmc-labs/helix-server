from rest_framework import serializers

from apps.crisis.models import Crisis


class CrisisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crisis
        # fields = '__all__'
        fields = ['id', 'countries', 'name', 'crisis_type']
