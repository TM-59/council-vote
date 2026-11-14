"""Local scaffold settings; credentials come from the process, never source code."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
SECRET_KEY = os.environ["COUNCIL_VOTE_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ["localhost", "testserver"]
ROOT_URLCONF = "council_vote.composition.urls"
INSTALLED_APPS = ["council_vote.infrastructure"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get(
            "COUNCIL_VOTE_DB_PATH", str(BASE_DIR / "test-results" / "council-vote.sqlite3")
        ),
        "TEST": {"NAME": str(BASE_DIR / "test-results" / "test-council-vote.sqlite3")},
    }
}
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
