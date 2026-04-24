from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .views import (
    ImportAhkLogView,
    ApplyRulesView,
    WindowActivityViewSet,
    ActivityBlockViewSet,
    UniqueActivityViewSet,
    ActivityRuleViewSet,
)

@api_view(['GET'])
def activities_root(request):
    """Activities API root."""
    return Response({
        'window-activities': f"{request.build_absolute_uri('/api/activities/window-activities/')}",
        'activity-blocks': f"{request.build_absolute_uri('/api/activities/activity-blocks/')}",
        'unique-activities': f"{request.build_absolute_uri('/api/activities/unique-activities/')}",
        'activity-rules': f"{request.build_absolute_uri('/api/activities/activity-rules/')}",
        'import': f"{request.build_absolute_uri('/api/activities/import/')}",
        'apply-rules': f"{request.build_absolute_uri('/api/activities/apply-rules/')}",
    })

router = DefaultRouter()
router.register(r"window-activities", WindowActivityViewSet, basename="window-activity")
router.register(r"activity-blocks", ActivityBlockViewSet, basename="activity-block")
router.register(r"unique-activities", UniqueActivityViewSet, basename="unique-activity")
router.register(r"activity-rules", ActivityRuleViewSet, basename="activity-rule")

urlpatterns = [
    path("", include(router.urls)),
    path("import/", ImportAhkLogView.as_view(), name="import-ahk-log"),
    path("apply-rules/", ApplyRulesView.as_view(), name="apply-rules"),
]
