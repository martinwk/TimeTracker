from datetime import datetime

from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from activities.importer import import_parsed_lines, parse_stream
from activities.rule_engine import apply_rules
from .models import WindowActivity, ActivityBlock, UniqueActivity, ActivityRule
from .serializers import (
    WindowActivitySerializer,
    ActivityBlockSerializer,
    UniqueActivitySerializer,
    ActivityRuleSerializer,
)


class ImportAhkLogView(APIView):
    """
    POST /api/activities/import/

    Accepteert een of meerdere AHK-logbestanden als multipart upload
    en importeert ze in de database.

    Request:  multipart/form-data met veld 'files' (meerdere bestanden toegestaan)
    Response: JSON met importresultaten per bestand
    """

    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.getlist("files")

        if not uploaded:
            return Response(
                {"error": "Geen bestanden aangeleverd. Gebruik veld 'files'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        for f in uploaded:
            result = import_parsed_lines(parse_stream(f))
            results.append({
                "filename": f.name,
                "imported": result.imported,
                "skipped_duplicates": result.skipped_duplicates,
                "skipped_parse_errors": result.skipped_parse_errors,
                "total_lines": result.total_lines,
            })

        total_imported = sum(r["imported"] for r in results)

        return Response(
            {"results": results, "total_imported": total_imported},
            status=status.HTTP_200_OK,
        )


class ApplyRulesView(APIView):
    """
    POST /api/activities/apply-rules/

    Voert alle actieve ActivityRules toe op UniqueActivities.

    Request body (optioneel):
    {
        "date": "2026-03-13",  # Enkelvoudige dag
        "date_from": "2026-03-01",  # Start van bereik
        "date_to": "2026-03-31"  # Einde van bereik
    }

    Response:
    {
        "mappings_created": 5,
        "mappings_skipped_manual": 2,
        "unique_activities_processed": 15
    }
    """

    def post(self, request):
        data = request.data or {}
        date_str = data.get("date")
        date_from_str = data.get("date_from")
        date_to_str = data.get("date_to")

        # Parse dates
        date_from = None
        date_to = None

        try:
            if date_str:
                date_from = date_to = datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_from_str:
                date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            if date_to_str:
                date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError as e:
            return Response(
                {"error": f"Ongeldige datum: {e}. Gebruik YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if date_from and date_to and date_from > date_to:
            return Response(
                {"error": "date_from moet voor date_to liggen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Voer regels uit
        result = apply_rules(date_from=date_from, date_to=date_to)

        return Response(
            {
                "mappings_created": result.mappings_created,
                "mappings_skipped_manual": result.mappings_skipped_manual,
                "unique_activities_processed": result.unique_activities_processed,
            },
            status=status.HTTP_200_OK,
        )


class WindowActivityViewSet(viewsets.ModelViewSet):
    queryset = WindowActivity.objects.all()
    serializer_class = WindowActivitySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["date", "app_name", "is_noise", "unique_activity"]
    ordering_fields = ["started_at", "date", "app_name"]
    ordering = ["-started_at"]


class ActivityBlockViewSet(viewsets.ModelViewSet):
    queryset = ActivityBlock.objects.all()
    serializer_class = ActivityBlockSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["date", "app_name"]
    ordering_fields = ["started_at", "date", "app_name"]
    ordering = ["-started_at"]


class UniqueActivityViewSet(viewsets.ModelViewSet):
    queryset = UniqueActivity.objects.all()
    serializer_class = UniqueActivitySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["block"]
    ordering_fields = ["total_seconds"]
    ordering = ["-total_seconds"]


class ActivityRuleViewSet(viewsets.ModelViewSet):
    queryset = ActivityRule.objects.all()
    serializer_class = ActivityRuleSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["project", "is_active"]
    ordering_fields = ["priority", "created_at"]
    ordering = ["priority"]
