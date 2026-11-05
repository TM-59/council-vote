import os
import secrets

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "council_vote.composition.settings")
os.environ.setdefault("COUNCIL_VOTE_SECRET_KEY", secrets.token_urlsafe(48))
django.setup()
