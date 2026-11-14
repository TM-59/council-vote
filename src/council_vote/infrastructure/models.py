"""Django persistence records; domain values are serialized by the repository."""

from django.db import models


class SessionRecord(models.Model):
    session_id: models.CharField[str, str] = models.CharField(max_length=128, primary_key=True)
    council: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    attempts_left: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    outcome: models.CharField[str | None, str | None] = models.CharField(
        max_length=4, null=True, blank=True
    )
    history: models.JSONField[list[dict[str, object]], list[dict[str, object]]] = models.JSONField(
        default=list
    )
    version: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(default=0)
