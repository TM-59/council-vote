"""Local scaffold settings; credentials come from the process, never source code."""

import os

SECRET_KEY = os.environ["COUNCIL_VOTE_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ["localhost", "testserver"]
ROOT_URLCONF = "council_vote.composition.urls"
INSTALLED_APPS = ["council_vote.infrastructure"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
