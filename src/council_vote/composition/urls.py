# Copyright 2026 TM-59
"""URL routes: the health endpoint only."""

from django.urls import path

from council_vote.presentation.views import health

urlpatterns = [path("health/", health, name="health")]
