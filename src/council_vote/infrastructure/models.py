# Copyright 2026 TM-59
"""Django persistence records; domain values are serialized by the repository."""

from django.db import models


class SessionRecord(models.Model):
    """One council session as stored: position, attempts, outcome and resolved history.

    `outcome` is the empty string while the session is still running.
    """

    session_id: models.CharField[str, str] = models.CharField(max_length=128, primary_key=True)
    council: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    attempts_left: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    outcome: models.CharField[str, str] = models.CharField(max_length=4, blank=True, default="")
    history: models.JSONField[list[dict[str, object]], list[dict[str, object]]] = models.JSONField(
        default=list
    )
    version: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        """Show the session identity, as the admin and the shell list records."""
        return self.session_id
