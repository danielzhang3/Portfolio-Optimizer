from rest_framework import serializers
from api.models import ATHSubmission

class ATHSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ATHSubmission
        fields = ['account_id', 'portfolioATHValue', 'portfolioATHDate', 'currentNAVValue', 'created_at', 'updated_at']
