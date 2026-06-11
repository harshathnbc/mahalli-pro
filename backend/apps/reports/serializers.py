"""DRF serializers for Reports & Export (Module 8)."""
from rest_framework import serializers

from apps.reports.models import ExportArtifact, LcReport, SimulatorScenario


class ExportArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportArtifact
        fields = ["id", "report", "kind", "file_ref", "sha256_hash", "generated_at"]
        read_only_fields = fields


class LcReportSerializer(serializers.ModelSerializer):
    artifacts = ExportArtifactSerializer(many=True, read_only=True)

    class Meta:
        model = LcReport
        fields = [
            "id", "compliance_year", "contract", "level", "type",
            "state", "computed_score", "created_at", "artifacts",
        ]
        read_only_fields = ["state", "computed_score", "created_at"]


class SimulatorScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulatorScenario
        fields = ["id", "scope", "inputs", "result", "created_at"]
        read_only_fields = ["result", "created_at"]
