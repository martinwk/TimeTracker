from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

@api_view(['GET'])
def api_root(request):
    """API root view met links naar alle sub-APIs."""
    return Response({
        'activities': reverse('activities-root', request=request),
        'projects': reverse('projects-root', request=request),
    })

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api_root, name="api-root"),
    path("api/activities/", include("apps.activities.urls")),
    path("api/projects/", include("apps.projects.urls")),
]
