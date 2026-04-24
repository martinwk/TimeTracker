from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .views import ProjectViewSet

@api_view(['GET'])
def projects_root(request):
    """Projects API root."""
    return Response({
        'projects': f"{request.build_absolute_uri('/api/projects/')}",
    })

router = DefaultRouter()
router.register(r"", ProjectViewSet, basename="project")

urlpatterns = [
    path("", include(router.urls)),
]
