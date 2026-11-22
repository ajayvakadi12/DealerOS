from rest_framework import serializers


class DisagreementSerializer(serializers.Serializer):
    reason = serializers.CharField()
    record_id = serializers.CharField(allow_null=True)
    entry_id = serializers.CharField(allow_null=True)
    owning_org = serializers.CharField()
    location = serializers.CharField()
    a_location = serializers.CharField(allow_null=True)
    b_location = serializers.CharField(allow_null=True)
    a_value = serializers.CharField(allow_null=True)
    b_value = serializers.CharField(allow_null=True)
    difference = serializers.CharField(allow_null=True)
    a_date = serializers.CharField(allow_null=True)
    b_date = serializers.CharField(allow_null=True)
    description = serializers.CharField()
    is_cross_tenant = serializers.BooleanField(default=False)
    details = serializers.JSONField(required=False, allow_null=True)


class SummaryMetricsSerializer(serializers.Serializer):
    total_disagreements = serializers.IntegerField()
    missing_in_b = serializers.IntegerField()
    orphan_in_b = serializers.IntegerField()
    duplicate_in_b = serializers.IntegerField()
    value_mismatch = serializers.IntegerField()
    location_mismatch = serializers.IntegerField()
    date_mismatch = serializers.IntegerField()
    voided_record_in_b = serializers.IntegerField()
