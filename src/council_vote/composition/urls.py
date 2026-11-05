from django.urls import path

from council_vote.presentation.views import health

urlpatterns = [path("health/", health, name="health")]
