from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from activities.importer import import_parsed_lines, parse_stream


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
