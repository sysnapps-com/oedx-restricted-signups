"""
tutor-contrib-restrictedsignup v1.3.0
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
#
# CORRECT APPROACH: Copy from installed Python package, not from build context.
# The template files are included in the package via MANIFEST.in and
# pyproject.toml [tool.setuptools.package-data], so they exist at:
#   /openedx/venv/lib/python*/site-packages/tutor_restrictedsignup/templates/...
#
# Docker COPY can access installed packages during the image build.
# ---------------------------------------------------------------------------
CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH = """
{% if RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE %}
# Copy custom email templates from the installed plugin package
# (guaranteed to exist because MANIFEST.in + pyproject.toml package-data includes them)
COPY --chown=app:app \\
  /openedx/venv/lib/python*/site-packages/tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt \\
  /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt

COPY --chown=app:app \\
  /openedx/venv/lib/python*/site-packages/tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt \\
  /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt

COPY --chown=app:app \\
  /openedx/venv/lib/python*/site-packages/tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html \\
  /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html

COPY --chown=app:app \\
  /openedx/venv/lib/python*/site-packages/tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt \\
  /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt

COPY --chown=app:app \\
  /openedx/venv/lib/python*/site-packages/tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html \\
  /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html

COPY --chown=app:app \\
  /openedx/venv/lib/python*/site-packages/tutor_restrictedsignup/templates/restrictedsignup/build/openedx/openedx/core/djangoapps/ace_common/templates/ace_common/edx_ace/common/base_body.html \\
  /openedx/edx-platform/openedx/core/djangoapps/ace_common/templates/ace_common/edx_ace/common/base_body.html
{% endif %}
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("openedx-dockerfile-post-python-requirements", CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH)
)

# ---------------------------------------------------------------------------
# 5. FORCE LEGACY INSTRUCTOR DASHBOARD
#
# CRITICAL FIX: Read template file lazily at hook registration time,
# not at module import time. This ensures ENV_TEMPLATE_ROOTS has been
# set up before we try to read the template.
# ---------------------------------------------------------------------------
def get_init_task_content():
    """Lazily read the init task template when the hook is registered"""
    return env.read_template_file(
        "restrictedsignup", "tasks", "lms", "init", "restrictedsignup.sh"
    )


# Register the init task with lazy loading
_init_filter = getattr(hooks.Filters, "CLI_DO_INIT_TASKS", None) or getattr(
    hooks.Filters, "COMMANDS_INIT", None
)
if _init_filter is not None:
    _init_filter.add_item(("lms", get_init_task_content()))
