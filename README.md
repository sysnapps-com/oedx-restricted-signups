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
| 5 | (optional, **on by default**) Forces the legacy Instructor Dashboard, where the CSV upload UI actually lives | Sets the `instructor.legacy_instructor_dashboard` waffle flag at LMS init |

**Why both #1 and #2 are needed:** disabling `ALLOW_PUBLIC_ACCOUNT_CREATION`
only blocks registration *server-side* — several operators report the
"Register" tab/button staying visible in the Authn MFE unless
`SHOW_REGISTRATION_LINKS` is also set to `False`. This plugin sets both, so
you get both effects (link hidden **and** the endpoint refuses signups if
someone hits it directly).

## ⚠️ Why you might not see the CSV upload section (#5, read this first)

As of the Open edX **Verawood** release (April 2026), the Instructor
Dashboard's default frontend was switched from the old server-rendered
pages to a new React micro-frontend, `frontend-app-instructor-dashboard`.

**The "Register/Enroll Students" CSV section — the one `ALLOW_AUTOMATED_SIGNUPS`
turns on, which creates full accounts (email, username, name, country) — was
never ported to the new dashboard.** Its Membership/Enrollments tab instead
sends unregistered emails a *pending enrollment invite* (they must still self-register).

Confirmed via Open edX's own GitHub issue tracker (`frontend-app-instructor-dashboard`
PR #233): the new dashboard's backend "does not enroll unregistered address[es]" the way the legacy CSV feature does.

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
| `RESTRICTEDSIGNUP_FORCE_LEGACY_DASHBOARD` | `True` | Master switch for #5 — see warning above |

Example — keep everything except the email-validation skip:

```bash
tutor config save --set RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION=false
tutor images build openedx
tutor local restart lms cms
```

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

## Custom email templates and branding

For custom email templates across your platform, use a dedicated email-templating plugin (separate project).
For logo and theme branding that applies uniformly across the LMS, use the Paragon theme plugin or a dedicated branding plugin.

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