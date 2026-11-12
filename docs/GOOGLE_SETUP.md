# Google Calendar setup (one-time, about 20 minutes)

The planner can write to your real Google Calendar through the Google Calendar API.
Google requires an "OAuth client" for that, and **only a person can create it** (it
needs your Google login). Without it everything still works offline: the demo writes
`.ics` files to `output/` that you can import into any calendar. Do this guide only if
you want the live Google Calendar demo.

> Google changes the console layout now and then. The menu names below match Google's
> own Python quickstart; if a label has moved, look for the closest one.
> Reference: https://developers.google.com/workspace/calendar/api/quickstart/python

**Only one of you needs to do steps 1 to 4.** The other person is added as a test user
(step 3) and receives `credentials.json` privately (step 5).

## 1. Create a Google Cloud project

1. Go to https://console.cloud.google.com and sign in with the Google account whose
   calendar you want to use (a personal `@gmail.com` account is simplest).
2. Click the project picker at the top, then **New Project**.
3. Name it `cosc329-study-planner` and click **Create**. Make sure it is selected.

No billing is needed; the Calendar API is free.

## 2. Enable the Google Calendar API

1. Open https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
2. Click **Enable**.

## 3. Configure the consent screen ("Google Auth platform")

1. Menu (☰) → **Google Auth platform** → **Branding**. If you see
   "Google Auth platform not configured yet", click **Get Started**.
2. **App Information**: App name `COSC329 Study Planner`, User support email = your
   email. Click **Next**.
3. **Audience**: choose **External**. (**Internal** is only available inside a Google
   Workspace organization; a normal Gmail account cannot pick it.) Click **Next**.
4. **Contact Information**: your email. Click **Next**.
5. Tick **I agree to the Google API Services: User Data Policy**, then **Continue**
   and **Create**.
6. Go to **Audience** (left menu). The app is in **Testing** mode. Under **Test users**
   click **Add users** and add **both** your and John's Google emails. Only listed
   test users can sign in. Save.
7. Go to **Data Access** → **Add or remove scopes** and add
   `https://www.googleapis.com/auth/calendar.events` (see and edit events on your
   calendars). Save. This is the only scope the planner asks for.

Leave the app in **Testing**. You do not need to publish or verify it for a class project.

## 4. Create the OAuth client and download `credentials.json`

1. Menu → **Google Auth platform** → **Clients** → **Create Client**.
2. **Application type**: **Desktop app**. Name: `study-planner-desktop`. Click **Create**.
3. Click **Download JSON** for the new client.
4. Rename the file to exactly **`credentials.json`** and move it into the repository
   root, the folder that contains `README.md` and `study_planner/`.

## 5. Keep it out of git (important)

`credentials.json` and the `token.json` created on first login are already in
`.gitignore`. Check before every commit:

```bash
git status
```

Neither file may appear in the list. **Never** commit, paste in an issue or post them in
a public chat: anyone with `token.json` can read and edit your calendar. If one leaks,
open **Google Auth platform → Clients**, delete the client and create a new one, and
revoke access at https://myaccount.google.com/permissions.

To let a teammate use the same project, send them `credentials.json` privately (direct
message, not the repository). Each person gets their own `token.json` when they sign in,
and each must be on the test user list from step 3.

## 6. First run

Activate the virtual environment and install the dependencies first (see the README).

**a) Safe smoke test.** The advanced student gets a rest day, so this only signs in,
reads your calendar and clears any old `[BayesPlanner]` events for today. It creates nothing.

```bash
python -m study_planner.cli demo --scenario advanced --google
```

A browser window opens. Sign in with one of the **test user** accounts. Google shows
"Google hasn't verified this app" because the app is in Testing mode: click
**Advanced → Go to COSC329 Study Planner (unsafe)** (it is your own app), tick the
calendar permission and **Continue**. The terminal then prints
`Written to your Google Calendar` and a file `token.json` appears. Later runs do not
ask you to sign in again.

**b) Real demo.** The struggling student gets a mandatory 5-hour block today:

```bash
python -m study_planner.cli demo --scenario struggling --google
```

Open Google Calendar: you should see **`[BayesPlanner] Intense 5-hour mandatory study
block`** today, with the exam, beliefs and expected utilities in its description. Take a
screenshot for the report (§8).

**c) Clean up.** Running the rest-day student again removes today's planner session
(and nothing else):

```bash
python -m study_planner.cli demo --scenario advanced --google
```

`--google` always needs `--scenario NAME`: each run replaces today's planner sessions,
so writing all five students would make them overwrite each other.

## Safety

The planner only ever deletes events whose title starts with `[BayesPlanner]`. Your own
events, lectures and exams are never touched (covered by tests in `tests/test_calendar.py`).
If you would rather not use your main calendar, create a second calendar in Google
Calendar and use its id instead: `GoogleCalendarClient` takes a `calendar_id` (default
`"primary"`), which you can pass in `write_to_google` in `study_planner/demo.py`. Find the
id under that calendar's *Settings and sharing → Integrate calendar*.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `FileNotFoundError: ... credentials.json not found` | The file is not in the repository root, or it has the wrong name (check it is not `credentials (1).json` or `client_secret_....json`). |
| Browser says **Error 403: access_denied** / "has not completed the Google verification process" | Your account is not on the **Test users** list (step 3.6). Add it, wait a minute, retry. |
| Browser says "Access blocked: authorisation error" for a school or work account | The organisation's admin blocks third-party apps. Use a personal Gmail account as a test user. |
| `HttpError 403 ... Google Calendar API has not been used in project ...` | Step 2 was skipped or was done in a different project. Enable the API in the project that owns the client; it can take a few minutes to apply. |
| `invalid_grant` / "Token has been expired or revoked" | In Testing mode Google expires sign-ins after about 7 days. Delete `token.json` and run again. |
| You changed the scope in the code | Delete `token.json` so Google asks for the new permission. |
| No browser window opens | Copy the URL printed in the terminal into a browser on the same computer; the sign-in returns to a `localhost` address that the program listens on. |
| Events show at the wrong hour | Times use `America/Vancouver` (`TIMEZONE` in `study_planner/config.py`). Change it there if your calendar uses another zone. |

## Checklist

- [x] Project created, Calendar API enabled
- [ ] Consent screen is **External / Testing**, both emails are test users
- [x] OAuth client type **Desktop app**, downloaded as `credentials.json` in the repo root
- [x] `git status` shows neither `credentials.json` nor `token.json`
- [x] `demo --scenario advanced --google` completes Google sign-in
- [x] `demo --scenario struggling --google` shows a 5-hour `[BayesPlanner]` block in Google Calendar
- [ ] Screenshot saved for REPORT.md §8

## Live verification — November 12, 2026

Sultan completed Google OAuth sign-in and confirmed the live calendar round trip:

1. Ran `demo --scenario advanced --google` and completed authentication.
2. Ran `demo --scenario struggling --google`. The supplied screenshot shows
   `[BayesPlanner] Intense 5-hour mandatory study block` on November 12,
   10:00–15:00, with model probabilities and expected utilities in its description.
3. Ran `demo --scenario advanced --google` again and confirmed that the study
   block disappeared.

`git check-ignore credentials.json token.json` confirms both credential files
are ignored. John's test-user access has not been independently verified.
The screenshot was supplied in chat; adding a report image remains a separate task.
