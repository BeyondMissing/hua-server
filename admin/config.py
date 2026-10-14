from pathlib import Path


ADMIN_DIR = Path(__file__).resolve().parent
STATIC_DIR = ADMIN_DIR / "static"
TEMPLATE_DIR = ADMIN_DIR / "templates"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
SESSION_TTL = 8 * 60 * 60

ACCOUNT_FIELDS = (
    "user_id",
    "login_name",
    "password_hash",
    "role_created",
    "banned",
    "enable_friends_application",
)
BOOL_FIELDS = (
    "role_created",
    "banned",
    "enable_friends_application",
)
