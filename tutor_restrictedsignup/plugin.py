"""
tutor-contrib-restrictedsignup v1.4.0
=====================================

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
# 4. TEMPLATE ROOT & TARGET MAPPINGS
# ---------------------------------------------------------------------------
# Register the plugin's package `templates/` directory
PACKAGE_TEMPLATES_DIR = str(
    importlib.resources.files("tutor_restrictedsignup") / "templates"
)
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(PACKAGE_TEMPLATES_DIR)

# Map templates in `templates/restrictedsignup/` to `env/plugins/restrictedsignup/`
hooks.Filters.ENV_TEMPLATE_TARGETS.add_item(
    ("restrictedsignup", "plugins")
)

CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH = """
{% if RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE %}
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html
COPY --chown=app:app plugins/restrictedsignup/build/openedx/openedx/core/djangoapps/ace_common/templates/ace_common/edx_ace/common/base_body.html /openedx/edx-platform/openedx/core/djangoapps/ace_common/templates/ace_common/edx_ace/common/base_body.html
{% endif %}
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("openedx-dockerfile-post-python-requirements", CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH)
)

# ---------------------------------------------------------------------------
# 5. FORCE LEGACY INSTRUCTOR DASHBOARD (SAFE LAZY LOAD)
# ---------------------------------------------------------------------------
def load_init_task():
    try:
        task_path = (
            importlib.resources.files("tutor_restrictedsignup")
            / "templates"
            / "restrictedsignup"
            / "tasks"
            / "lms"
            / "init"
            / "restrictedsignup.sh"
        )
        return task_path.read_text(encoding="utf-8")
    except Exception:
        return ""

_init_filter = getattr(hooks.Filters, "CLI_DO_INIT_TASKS", None) or getattr(
    hooks.Filters, "COMMANDS_INIT", None
)
if _init_filter is not None:
    _init_filter.add_item(("lms", load_init_task()))