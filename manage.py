"""Local development entry; generate an ephemeral key without storing credentials."""

import os
import secrets
import sys

from django.core.management import execute_from_command_line

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "council_vote.composition.settings")
os.environ.setdefault("COUNCIL_VOTE_SECRET_KEY", secrets.token_urlsafe(48))
execute_from_command_line(sys.argv)
