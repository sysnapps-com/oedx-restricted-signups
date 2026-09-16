# tutor-contrib-restrictedsignup

Repository: https://github.com/sysnapps-com/oedx-restricted-signups

A Tutor plugin for Open edX that closes public self-registration and makes
**instructor-driven CSV upload** (Instructor Dashboard → Membership →
"Register/Enroll Students") the sole way new learners get an account and a
course enrollment.

## What it does

| # | Effect | How |
|---|--------|-----|
| 1 | Public registration disabled on the backend | `FEATURES["ALLOW_PUBLIC_ACCOUNT_CREATION"] = False` in LMS + CMS |
| 2 | "Register" link/button hidden in the Authn MFE login page | `SHOW_REGISTRATION_LINKS = False` (+ mirrored into `MFE_CONFIG`) |
| 3 | Instructor CSV account-creation + enrollment enabled | `FEATURES["ALLOW_AUTOMATED_SIGNUPS"] = True` |
| 4 | (optional, on by default) New CSV-created accounts skip the email-confirmation step | `FEATURES["SKIP_EMAIL_VALIDATION"] = True` |
| 5 | (optional, off by default) Custom email sent to CSV-created users | Overrides the ACE email templates in the image |
| 6 | (optional, **on by default**) Forces the legacy Instructor Dashboard, where the CSV upload UI actually lives | Sets the `instructor.legacy_instructor_dashboard` waffle flag at LMS init |

**Why both #1 and #2 are needed:** disabling `ALLOW_PUBLIC_ACCOUNT_CREATION`
only blocks registration *server-side* — several operators report the
"Register" tab/button staying visible in the Authn MFE unless
`SHOW_REGISTRATION_LINKS` is also set to `False`. This plugin sets both, so
you get both effects (link hidden **and** the endpoint refuses signups if
someone hits it directly).

## ⚠️ Why you might not see the CSV upload section (#6, read this first)

As of the Open edX **Verawood** release (April 2026), the Instructor
Dashboard's default frontend was switched from the old server-rendered
pages to a new React micro-frontend, `frontend-app-instructor-dashboard`.

**The "Register/Enroll Students" CSV section — the one `ALLOW_AUTOMATED_SIGNUPS`
turns on, which creates full accounts (email, username, name, country) — was
never ported to the new dashboard.** Its Membership/Enrollments tab instead
sends unregistered emails a *pending enrollment invite* (they must still
self-register), which is a materially different, weaker behavior than what
you asked for.

Confirmed via Open edX's own GitHub issue tracker (`frontend-app-instructor-dashboard`
PR #233): the new dashboard's backend "does not enroll unregistered
add[resses]" the way the legacy CSV feature does.

**The fix:** Open edX ships a waffle flag, `instructor.legacy_instructor_dashboard`,
that reverts to the old dashboard. This plugin sets it to `True` for everyone
automatically, at LMS init time (`RESTRICTEDSIGNUP_FORCE_LEGACY_DASHBOARD`,
default `True`). If you've already deployed and don't see the CSV section,
this is almost certainly why — rerun `tutor local do init` (or redeploy) after
upgrading this plugin.

**Be aware this is a stopgap, not a permanent fix.** The legacy dashboard is
formally deprecated ([DEPR ticket #38432](https://github.com/openedx/openedx-platform/issues/38432)),
with removal tied to the new dashboard reaching feature parity. There is no
committed removal date as of this writing, but treat this as something to
revisit periodically — check that DEPR ticket, and re-test this plugin,
before every Open edX upgrade. If/when the legacy dashboard is removed
without a replacement for automated signups, this plugin's core premise
(#3) will need to be replaced with whatever mechanism replaces it.

## What "instructor CSV upload" actually does (verified)

With `ALLOW_AUTOMATED_SIGNUPS = True`, course teams get a **"Register/Enroll
Students"** section in Instructor Dashboard → Membership, separate from the
ordinary "Batch Enrollment" box (which only works on *existing* users).

They upload a CSV with **exactly these columns, in this order, no header
row**:

```
email,username,name,country_code
jane@example.com,janedoe,Jane Doe,US
```

For each row, Open edX will, in one step:
1. Create the user account if it doesn't already exist, with a random password
2. Enroll that user in the current course
3. Send the user an email with their login credentials (or an enrollment
   notice, if the account already existed)

This matches what you described — it's a real, supported path, not a
workaround.

## Installation

```bash
pip install git+https://github.com/sysnapps-com/oedx-restricted-signups.git
# or, if published to PyPI:
# pip install tutor-contrib-restrictedsignup

tutor plugins enable restrictedsignup
tutor config save
tutor images build openedx        # required — patches touch the Dockerfile
tutor local launch                # runs init automatically, incl. the waffle flag (see below)
```

If you're upgrading an **existing** running instance rather than doing a
fresh `launch`, run init explicitly after rebuilding — `restart` alone does
not re-run init tasks:
```bash
tutor images build openedx
tutor local start -d
tutor local do init --limit lms
```

## Requirements

Requires `tutor>=17.0.0`. No upper version cap — tested against Tutor
19.x–22.x. If you hit an incompatibility with a very new Tutor release,
open an issue; don't just delete the version pin locally without reporting
it, so the fix lands for everyone.

## Configuration

All settings are booleans, changeable with `tutor config save --set NAME=value`:

| Setting | Default | Purpose |
|---|---|---|
| `RESTRICTEDSIGNUP_DISABLE_PUBLIC_REGISTRATION` | `True` | Master switch for #1 |
| `RESTRICTEDSIGNUP_ENABLE_AUTOMATED_SIGNUPS` | `True` | Master switch for #3 |
| `RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS` | `True` | Master switch for #2 |
| `RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION` | `True` | Master switch for #4 |
| `RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE` | `False` | Master switch for #5 |
| `RESTRICTEDSIGNUP_FORCE_LEGACY_DASHBOARD` | `True` | Master switch for #6 — see warning above |

Example — keep everything except the email-validation skip:

```bash
tutor config save --set RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION=false
tutor images build openedx
tutor local restart lms cms
```

## Custom email template (optional, `RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE`)

edx-platform's "account created + enrolled" ACE email is made of **5 files**,
all under:
```
tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/
  subject.txt      — email subject line
  body.txt         — plain-text fallback body
  body.html        — HTML body
  from_name.txt    — sender display name
  head.html        — <style>/CSS block used by body.html
```
(Confirmed against a real Sumac-based Tutor deployment — your release may
differ, always verify per step 1 below.)

Every one of these ships as a **placeholder clearly marked "REPLACE THIS
FILE"** — not your platform's real wording — because the exact content is
Open-edX-release-specific and this plugin cannot know it in advance.

### Steps to customize

1. **Pull your platform's real template files.** Confirm the filenames match
   first (they can shift between releases):
   ```bash
   tutor local exec lms find /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment -type f
   ```
   Then extract each one's real content, e.g.:
   ```bash
   tutor local exec lms cat /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/subject.txt
   tutor local exec lms cat /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.txt
   tutor local exec lms cat /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/body.html
   tutor local exec lms cat /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/from_name.txt
   tutor local exec lms cat /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/head.html
   ```
2. **Replace each placeholder file's content** in this plugin with what you
   extracted, then edit the wording/branding as you like. Every `{{ var }}`
   you keep must already exist in the original — don't invent new variable
   names, since edx-platform (not this plugin) supplies their values at
   send time.

   **Critical — keep the `{% raw %}` / `{% endraw %}` wrapper around your
   content.** Tutor renders every template file through its own Jinja
   engine before the file ever reaches edx-platform. `{{ platform_name }}`,
   `{{ site_name }}`, etc. are **Django/ACE variables**, meant to be filled
   in later by edx-platform when it actually sends the email — not by
   Tutor. If you paste your extracted content in *without* the `{% raw %}`
   wrapper, Tutor's Jinja will try to resolve those variables itself at
   build time, using its own (different) config namespace, and fail with
   an error like:
   ```
   Error rendering template ... Error: Missing configuration value: 'site_name' is undefined
   ```
   The fix is always the same: wrap your real content in `{% raw %}` at
   the top and `{% endraw %}` at the bottom, exactly as the shipped
   placeholders already do — don't remove those tags when you replace the
   text inside them.
3. If your `find` output shows **different filenames** than the 5 above,
   rename the files in this plugin to match, and update the `COPY` lines in
   `tutor_restrictedsignup/plugin.py` (`CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH`)
   accordingly.
4. Enable and rebuild:
   ```bash
   tutor config save --set RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE=true
   tutor images build openedx
   tutor local restart lms cms
   ```
5. **Test before relying on it**: trigger a real CSV upload against a test
   course/user and check the email that arrives, in both HTML and plain-text
   mail clients.

This ships **off by default**, and every template ships as an obvious
placeholder rather than a guessed-at real template, precisely because both
the filenames and their content are version-sensitive — never enable this
without first swapping in your platform's real templates.

## Known caveats / things to check on your platform

- **Third-party auth (SSO/SAML/OAuth)**: if you also allow login via an
  external identity provider, that path is untouched by this plugin. Users
  could still create accounts through SSO auto-provisioning. Disable that
  separately if it's not wanted.
- **Direct API access**: this plugin does not lock down the registration
  REST API beyond what `ALLOW_PUBLIC_ACCOUNT_CREATION` already does at the
  platform level — that flag is the authoritative gate edx-platform checks
  before creating an account via any registration entry point.
- **`SKIP_EMAIL_VALIDATION` is global**: once enabled it applies to any
  account-creation path, not just CSV uploads. That's normally fine here,
  since public registration is disabled and CSV upload becomes the only
  route — but double check if you have another account-creation mechanism
  (e.g. a custom SSO pipeline) where you *do* want email confirmation.
- **CSV upload is not built for scale**: Open edX's own docs note batch
  enrollment/account-creation via this screen is intended for smaller
  courses, not massive ones. For very large cohorts, consider the
  bulk-enroll REST API instead.

## Uninstall / revert

```bash
tutor plugins disable restrictedsignup
tutor images build openedx
tutor local start -d
tutor local do init --limit lms   # needed if you want the waffle flag reverted
tutor local restart lms cms
```

Disabling the plugin stops it from *re-asserting* the
`instructor.legacy_instructor_dashboard` waffle flag, but does not itself
flip an already-set flag back off — Tutor plugins don't run "uninstall"
scripts. If you need the new dashboard back, turn the flag off manually
via Django admin (`/admin/waffle/flag/`) or:
```bash
tutor local exec lms ./manage.py lms shell -c "
from waffle.models import Flag
Flag.objects.filter(name='instructor.legacy_instructor_dashboard').update(everyone=False)
"
```
