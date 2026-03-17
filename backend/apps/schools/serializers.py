from rest_framework import serializers
from .models import School

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name', 'code', 'province', 'city', 'district', 'category']
