from django.urls import path

from .views import ImportAhkLogView

urlpatterns = [
    path("activities/import/", ImportAhkLogView.as_view(), name="import-ahk-log"),
]
