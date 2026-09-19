"""
tutor-contrib-restrictedsignup v.1.5.0
=======================================

Disables public self-registration on an Open edX platform run with Tutor,
and turns on the instructor-driven "Register/Enroll Students" CSV upload
feature (Instructor Dashboard > Membership) as the sole account-creation +
enrollment path.
"""

import importlib.resources
from tutor import hooks

# ---------------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------------
hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        ("RESTRICTEDSIGNUP_DISABLE_PUBLIC_REGISTRATION", True),
        ("RESTRICTEDSIGNUP_ENABLE_AUTOMATED_SIGNUPS", True),
        ("RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS", True),
        ("RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION", True),
        ("RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE", False),
        ("RESTRICTEDSIGNUP_FORCE_LEGACY_DASHBOARD", True),
        ("RESTRICTEDSIGNUP_EMAIL_LOGO_URL", ""),
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
# 3. HIDE REGISTRATION LINKS
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
# 4. CUSTOM EMAIL TEMPLATES 
# ---------------------------------------------------------------------------
# Register the plugin's package `templates/` directory
PACKAGE_TEMPLATES_DIR = str(
    importlib.resources.files("tutor_restrictedsignup") / "templates"
)
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(PACKAGE_TEMPLATES_DIR)

# Render files from the plugin's `templates/restrictedsignup/build/openedx/`
# directly into the openedx image build context: `env/build/openedx/restrictedsignup_custom/`
hooks.Filters.ENV_TEMPLATE_TARGETS.add_item(
    ("restrictedsignup/build/openedx", "build/openedx/restrictedsignup_custom")
)

# Docker build context for 'openedx' is `env/build/openedx/`. 
# We copy relative to that context root.
CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH = """
{% if RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE %}
COPY --chown=app:app restrictedsignup_custom/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt
COPY --chown=app:app restrictedsignup_custom/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt
COPY --chown=app:app restrictedsignup_custom/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html
COPY --chown=app:app restrictedsignup_custom/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt
COPY --chown=app:app restrictedsignup_custom/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html
COPY --chown=app:app restrictedsignup_custom/openedx/core/djangoapps/ace_common/templates/ace_common/edx_ace/common/base_body.html /openedx/edx-platform/openedx/core/djangoapps/ace_common/templates/ace_common/edx_ace/common/base_body.html
{% endif %}
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("openedx-dockerfile-post-python-requirements", CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH)
)

# ---------------------------------------------------------------------------
# 5. FORCE LEGACY INSTRUCTOR DASHBOARD
# ---------------------------------------------------------------------------
INIT_TASK = """#!/bin/bash
set -e

echo "tutor-contrib-restrictedsignup: enabling instructor.legacy_instructor_dashboard waffle flag"
./manage.py lms shell -c "
from waffle.models import Flag
flag, _ = Flag.objects.get_or_create(name='instructor.legacy_instructor_dashboard')
flag.everyone = True
flag.save()
print('instructor.legacy_instructor_dashboard set to: everyone=True')
"
"""

_init_filter = getattr(hooks.Filters, "CLI_DO_INIT_TASKS", None) or getattr(
    hooks.Filters, "COMMANDS_INIT", None
)
if _init_filter is not None:
    _init_filter.add_item(("lms", INIT_TASK))