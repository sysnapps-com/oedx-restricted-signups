"""
tutor-contrib-restrictedsignup
===============================

Disables public self-registration on an Open edX platform run with Tutor,
and turns on the instructor-driven "Register/Enroll Students" CSV upload
feature (Instructor Dashboard > Membership) as the sole account-creation +
enrollment path.

See README.md for full documentation, verified behavior, and known caveats.
"""
import importlib.resources

from tutor import hooks

# ---------------------------------------------------------------------------
# 1. CONFIGURATION — toggles the operator can override with
#    `tutor config save --set RESTRICTEDSIGNUP_XXX=...`
# ---------------------------------------------------------------------------
hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        # Master switches -----------------------------------------------------
        ("RESTRICTEDSIGNUP_DISABLE_PUBLIC_REGISTRATION", True),
        ("RESTRICTEDSIGNUP_ENABLE_AUTOMATED_SIGNUPS", True),
        ("RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS", True),
        # Skips the "confirm your email" step for accounts created via the
        # instructor CSV upload, so students can log in with the password
        # they're emailed immediately. Safe to leave True once public
        # self-registration is disabled, since this is then the only account
        # creation path.
        ("RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION", True),
        # Set to True only after you have edited the template files under
        # tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/
        # templates/instructor/edx_ace/accountcreationandenrollment/email/
        # and rebuilt the openedx image. See README "Custom email template".
        ("RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE", False),
    ]
)

# ---------------------------------------------------------------------------
# 2. CORE FEATURE FLAGS — injected into LMS *and* CMS common settings
#    (both services need to agree, since Studio also checks these flags
#    e.g. when course teams manage enrollment).
# ---------------------------------------------------------------------------
CORE_SETTINGS = """
{% if RESTRICTEDSIGNUP_DISABLE_PUBLIC_REGISTRATION %}
# --- tutor-contrib-restrictedsignup: disable public self-registration ---
FEATURES["ALLOW_PUBLIC_ACCOUNT_CREATION"] = False
{% endif %}
{% if RESTRICTEDSIGNUP_ENABLE_AUTOMATED_SIGNUPS %}
# --- tutor-contrib-restrictedsignup: enable instructor CSV account creation + enrollment ---
FEATURES["ALLOW_AUTOMATED_SIGNUPS"] = True
{% endif %}
{% if RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION %}
# --- tutor-contrib-restrictedsignup: skip email confirmation for auto-created accounts ---
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
# 3. HIDE THE "REGISTER" LINK/BUTTON IN THE AUTHN MFE
#
#    Disabling ALLOW_PUBLIC_ACCOUNT_CREATION blocks registration on the
#    backend, but by itself it does NOT remove the "Register" link/button
#    from the login page rendered by the Authn micro-frontend — that is a
#    separate, front-end-only setting read from MFE_CONFIG. Both are needed.
# ---------------------------------------------------------------------------
MFE_SETTINGS = """
{% if RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS %}
SHOW_REGISTRATION_LINKS = False
{% endif %}
"""

hooks.Filters.ENV_PATCHES.add_items(
    [
        ("openedx-lms-common-settings", MFE_SETTINGS),
        # Also propagate into MFE_CONFIG so the Authn/frontend-base MFE build
        # picks it up (some MFE versions read this key directly).
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
# 4. OPTIONAL: CUSTOM EMAIL TEMPLATE FOR AUTO-CREATED ACCOUNTS
#
#    edx-platform renders the "you've been added to a course" email via ACE
#    templates at:
#      lms/templates/instructor/edx_ace/accountcreationandenrollment/email/
#
#    This plugin ships editable copies of those templates (see
#    tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/...)
#    and, when enabled, copies them into the openedx image at build time,
#    overriding the stock ones.
#
#    IMPORTANT: exact filenames/format can shift between Open edX releases.
#    Before enabling this in production, confirm the real filenames inside
#    your running LMS container:
#      tutor local exec lms find /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment -type f
#    and rename the files under templates/.../email/ in this plugin to match.
# ---------------------------------------------------------------------------
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    str(importlib.resources.files("tutor_restrictedsignup") / "templates")
)
hooks.Filters.ENV_TEMPLATE_TARGETS.add_item(("restrictedsignup/build", "plugins"))

CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH = """
{% if RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE %}
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html
{% endif %}
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("openedx-dockerfile-post-python-requirements", CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH)
)
