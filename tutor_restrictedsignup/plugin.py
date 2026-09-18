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

from tutor import env, hooks

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
        # ALLOW_AUTOMATED_SIGNUPS's "Register/Enroll Students" CSV section
        # only exists on the LEGACY (pre-Verawood) Instructor Dashboard.
        # Open edX's new React instructor dashboard, default since the
        # Verawood release (openedx/openedx-platform#38396, merged
        # 2026-04-23), does not have this feature — it treats unregistered
        # emails as a pending invite, not a full account-creation flow.
        # This toggle flips the `instructor.legacy_instructor_dashboard`
        # waffle flag to True at LMS init time so the feature is actually
        # reachable. See README "Why am I not seeing the CSV upload
        # section?" for the deprecation timeline and caveats.
        ("RESTRICTEDSIGNUP_FORCE_LEGACY_DASHBOARD", True),
        # Only used when RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE is True.
        # The legacy Instructor Dashboard's account-creation email uses
        # {{ logo_url }} in its base template, which resolves to the
        # DEFAULT theme's logo even when the rest of the site correctly
        # runs a custom theme (e.g. Paragon-based) — the legacy dashboard
        # renders emails in a different context that doesn't pick up the
        # active theme. Set this to your own hosted logo image URL to fix
        # the branding shown in these emails specifically.
        ("RESTRICTEDSIGNUP_EMAIL_LOGO_URL", ""),
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
#    This plugin ships 5 files (subject.txt, body.txt, body.html,
#    from_name.txt, head.html) as PLACEHOLDERS clearly marked
#    "REPLACE THIS FILE" — before enabling, confirm the real filenames/
#    content inside your running LMS container:
#      tutor local exec lms find /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment -type f
#    then replace each placeholder's content with your platform's real
#    template (via `tutor local exec lms cat <path>`) before customizing.
# ---------------------------------------------------------------------------
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    str(importlib.resources.files("tutor_restrictedsignup") / "templates")
)
hooks.Filters.ENV_TEMPLATE_TARGETS.add_item(("restrictedsignup/build", "build/openedx"))

CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH = """
{% if RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE %}
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt
COPY --chown=app:app plugins/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html
# The base ACE email template (logo, header, footer) shared by ALL instructor
# ACE emails (account creation, enrollment, beta tester add/remove, etc).
# Overridden here specifically to fix the logo not respecting the active
# theme when rendered from the legacy Instructor Dashboard — see
# RESTRICTEDSIGNUP_EMAIL_LOGO_URL. This changes the header/footer for every
# email in this list, not just account-creation.
COPY --chown=app:app plugins/restrictedsignup/build/openedx/openedx/core/djangoapps/ace_common/templates/ace_common/edx_ace/common/base_body.html /openedx/edx-platform/openedx/core/djangoapps/ace_common/templates/ace_common/edx_ace/common/base_body.html
{% endif %}
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("openedx-dockerfile-post-python-requirements", CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH)
)

# ---------------------------------------------------------------------------
# 6. FORCE THE LEGACY INSTRUCTOR DASHBOARD (where ALLOW_AUTOMATED_SIGNUPS
#    actually lives — see the long comment on
#    RESTRICTEDSIGNUP_FORCE_LEGACY_DASHBOARD above).
#
#    This runs as an LMS init task, since a waffle flag is a database row,
#    not a Django setting — it can't be set via ENV_PATCHES.
# ---------------------------------------------------------------------------
INIT_TASK_CONTENT = env.read_template_file(
    "restrictedsignup", "tasks", "lms", "init", "restrictedsignup.sh"
)
# Filter name has changed across Tutor releases (COMMANDS_INIT in some
# versions, CLI_DO_INIT_TASKS in others) — use whichever this install has.
_init_filter = getattr(hooks.Filters, "CLI_DO_INIT_TASKS", None) or getattr(
    hooks.Filters, "COMMANDS_INIT", None
)
if _init_filter is not None:
    _init_filter.add_item(("lms", INIT_TASK_CONTENT))
