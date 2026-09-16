# tutor-contrib-restrictedsignup

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

**Why both #1 and #2 are needed:** disabling `ALLOW_PUBLIC_ACCOUNT_CREATION`
only blocks registration *server-side* — several operators report the
"Register" tab/button staying visible in the Authn MFE unless
`SHOW_REGISTRATION_LINKS` is also set to `False`. This plugin sets both, so
you get both effects (link hidden **and** the endpoint refuses signups if
someone hits it directly).

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
tutor local launch                # or: tutor local restart lms cms
```

## Configuration

All settings are booleans, changeable with `tutor config save --set NAME=value`:

| Setting | Default | Purpose |
|---|---|---|
| `RESTRICTEDSIGNUP_DISABLE_PUBLIC_REGISTRATION` | `True` | Master switch for #1 |
| `RESTRICTEDSIGNUP_ENABLE_AUTOMATED_SIGNUPS` | `True` | Master switch for #3 |
| `RESTRICTEDSIGNUP_HIDE_REGISTRATION_LINKS` | `True` | Master switch for #2 |
| `RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION` | `True` | Master switch for #4 |
| `RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE` | `False` | Master switch for #5 |

Example — keep everything except the email-validation skip:

```bash
tutor config save --set RESTRICTEDSIGNUP_SKIP_EMAIL_VALIDATION=false
tutor images build openedx
tutor local restart lms cms
```

## Custom email template (optional, `RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE`)

1. Edit the files under:
   ```
   tutor_restrictedsignup/templates/restrictedsignup/build/openedx/lms/templates/instructor/edx_ace/accountcreationandenrollment/email/
     subject.txt
     body.html
   ```
2. **Before relying on this in production**, confirm the real template
   filenames/format in your own image — they can change between Open edX
   releases:
   ```bash
   tutor local exec lms find /openedx/edx-platform/lms/templates/instructor/edx_ace/accountcreationandenrollment -type f
   ```
   If the filenames differ, rename the files in this plugin to match, and
   update the `COPY` lines in `tutor_restrictedsignup/plugin.py`
   (`CUSTOM_EMAIL_TEMPLATE_DOCKERFILE_PATCH`) accordingly.
3. Enable and rebuild:
   ```bash
   tutor config save --set RESTRICTEDSIGNUP_CUSTOM_EMAIL_TEMPLATE=true
   tutor images build openedx
   tutor local restart lms cms
   ```

This ships **off by default** precisely because template paths are
version-sensitive — verify before turning it on.

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
tutor local restart lms cms
```
