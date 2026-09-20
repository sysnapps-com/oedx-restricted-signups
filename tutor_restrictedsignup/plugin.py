"""
tutor-contrib-restrictedsignup v1.6.0
=======================================

Disables public self-registration on an Open edX platform run with Tutor,
and turns on the instructor-driven "Register/Enroll Students" CSV upload
feature (Instructor Dashboard > Membership) as the sole account-creation +
enrollment path.

See README.md for full documentation, verified behavior, and known caveats.
"""
import importlib.resources

from tutor import env, hooks

# ---------------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------------
hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        ("RESTRICTEDSIGNUP_DISABLE_PUBLIC_REGISTRATION", True),
        ("RESTRICTEDSIGNUP_ENABLE_AUTOMATED_SIGNUPS", True),
        ("RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS", True),
        ("RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION", True),
        ("RESTRICTEDSIGNUP_FORCE_LEGACY_DASHBOARD", True),
    ]
)

# ---------------------------------------------------------------------------
# 2. CORE FEATURE FLAGS
# ---------------------------------------------------------------------------
CORE_SETTINGS = """
{% if RESTRICTEDSIGNUP_DISABLE_PUBLIC_REGISTRATION %}
FEATURES["ALLOW_PUBLIC_ACCOUNT_CREATION"] = False
{% endif %}
{% if RESTRICTEDSIGNUP_ENABLE_AUTOMATED_SIGNUPS %}
FEATURES["ALLOW_AUTOMATED_SIGNUPS"] = True
{% endif %}
{% if RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION %}
FEATURES["SKIP_EMAIL_VALIDATION"] = True
{% endif %}
"""

hooks.Filters.ENV_PATCHES.add_items(
    [
        ("openedx-lms-common-settings", CORE_SETTINGS),
        ("openedx-cms-common-settings", CORE_SETTINGS),
    ]
)

# ---------------------------------------------------------------------------
# 3. HIDE REGISTRATION LINKS IN AUTHN MFE
# ---------------------------------------------------------------------------
MFE_SETTINGS = """
{% if RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS %}
SHOW_REGISTRATION_LINKS = False
{% endif %}
"""

hooks.Filters.ENV_PATCHES.add_items(
    [
        ("openedx-lms-common-settings", MFE_SETTINGS),
        (
            "openedx-lms-production-settings",
            """
{% if RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS %}
MFE_CONFIG["SHOW_REGISTRATION_LINKS"] = False
{% endif %}
""",
        ),
        (
            "openedx-lms-development-settings",
            """
{% if RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS %}
MFE_CONFIG["SHOW_REGISTRATION_LINKS"] = False
{% endif %}
""",
        ),
    ]
)

# ---------------------------------------------------------------------------
# 4. FORCE LEGACY INSTRUCTOR DASHBOARD (inline task, no file reading)
# ---------------------------------------------------------------------------
INIT_TASK = """
#!/bin/bash
set -e

echo "tutor-contrib-restrictedsignup: enabling instructor.legacy_instructor_dashboard waffle flag"
./manage.py lms shell -c "
from waffle.models import Flag
flag, created = Flag.objects.get_or_create(name='instructor.legacy_instructor_dashboard')
flag.everyone = True
flag.save()
print('✓ instructor.legacy_instructor_dashboard set to: everyone=True')
"
"""

_init_filter = getattr(hooks.Filters, "CLI_DO_INIT_TASKS", None) or getattr(
    hooks.Filters, "COMMANDS_INIT", None
)
if _init_filter is not None:
    _init_filter.add_item(("lms", INIT_TASK))
