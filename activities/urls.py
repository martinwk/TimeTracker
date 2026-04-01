from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ImportAhkLogView,
    ApplyRulesView,
    WindowActivityViewSet,
    ActivityBlockViewSet,
    UniqueActivityViewSet,
    ActivityRuleViewSet,
)

router = DefaultRouter()
router.register(r"window-activities", WindowActivityViewSet, basename="window-activity")
router.register(r"activity-blocks", ActivityBlockViewSet, basename="activity-block")
router.register(r"unique-activities", UniqueActivityViewSet, basename="unique-activity")
router.register(r"activity-rules", ActivityRuleViewSet, basename="activity-rule")

urlpatterns = [
    path("", include(router.urls)),
    path("activities/import/", ImportAhkLogView.as_view(), name="import-ahk-log"),
    path("activities/apply-rules/", ApplyRulesView.as_view(), name="apply-rules"),
]
