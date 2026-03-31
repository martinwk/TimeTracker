from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from activities.importer import import_parsed_lines, parse_stream
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
