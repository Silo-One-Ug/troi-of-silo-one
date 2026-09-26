---
title: Your Google account
description: "Gmail, Calendar, Drive, Docs, Sheets, Slides, Tasks and Contacts through the Google Workspace tool server: what Troi may do there, the scopes it holds, the one-time way in, and the way out."
order: 13
---

Troi can work in your Google account: read and search your mail and write drafts, read and create
calendar events, find, read and organise files in Drive, read and write Docs, Sheets and Slides,
keep Tasks, look up Contacts. The tools come from the open-source Google Workspace MCP server,
installed on the Mac and run as one of the brain's tool servers (`troi-console/google.sh mcp`) over
stdio, signed in as you, once, through an OAuth client of your own. Nothing leaves the Mac but the
calls to Google's own APIs.

## What it may do

- **Reading, searching, drafting and creating are Troi's**: "what's in my inbox from the bank",
  "draft a reply to Sarah", "put the launch on my Google calendar on the first at nine", "find the
  budget sheet in Drive and read the totals", "add a task for Monday".
- **Troi does not send email.** Gmail is held at the "drafts" level: it reads, searches, labels and
  writes drafts; the send button is yours. Sharing a file or document, or answering an invitation,
  still needs your explicit go-ahead in the same turn.
- **Nothing there is ever deleted, trashed or emptied.** The guard blocks those tools by name, as it
  blocks deletion everywhere else; Troi says so and stops.
- Google Calendar is the account's own calendar there. The Mac's Calendar app still works as before
  and shows the same events when the account is on this Mac.

## The way in, once

Google gives access through an OAuth client of your own, in a Google Cloud project. Five minutes,
and only you can do it:

1. In [Google Cloud](https://console.cloud.google.com), pick a project (any; a new one called Troi
   is fine). Under **APIs & Services › OAuth consent screen**: External, an app name, your email,
   and yourself under test users. Under **Credentials › Create credentials › OAuth client ID**: a
   **Web application**, with `http://localhost:8788/oauth2callback` as an authorised redirect URI.
   Download the JSON.
2. On the Mac:

   ```bash
   troi-console/google.sh setup ~/Downloads/client_secret_….json   # kept as data/google/client_secret.json
   troi-console/google.sh enable                                    # the APIs, in the gcloud project (or turn them on in the console)
   troi-console/google.sh signin you@gmail.com                      # the consent screen opens in the browser; approve it
   ```

3. Start Troi again, or `kill -USR1 "$(cat data/cache/voice.pid)"` to restart the voice line in
   place. `troi-console/google.sh status` says where things stand, and the doctor checks it.

While the app on Google's side is "In testing", Google signs it out after seven days and the
sign-in has to be repeated; setting the app to "In production" (no verification is needed for your
own account; the consent screen shows a warning you click through) makes the sign-in stay.

If a tool ever answers that it needs authentication, Troi gives you the sign-in link in the console
or on Telegram and waits; the sign-in is yours.

## Where things are

| Thing | Where |
| --- | --- |
| The OAuth client | `data/google/client_secret.json` (0600) |
| The sign-in (refresh token) | `data/google/credentials/<email>.json`; never in the record, never backed up |
| The callback the sign-in returns to | `http://localhost:8788/oauth2callback` |
| The APIs | Gmail, Calendar, Drive, Docs, Sheets, Slides, Tasks, People (`google.sh enable`) |
| The server | `workspace-mcp`, installed by `install.sh` as a uv tool (`google.sh status` names the runner) |

What you read and write there goes to Google as with any client; the mail and files Troi reads to
answer a question go to the model as part of the conversation, like a file it is pointed at.

## The scopes it holds

The server asks Google for the narrowest scopes it offers per service, set in one place
(`PERMISSIONS` in `troi-console/google.py`; `google.sh permissions` prints them):

| Service | Level | What that allows |
| --- | --- | --- |
| Gmail | drafts | read and search mail, labels, write drafts; **no sending** |
| Calendar | full | read, create, change and cancel events |
| Drive | full | find, read, create, move and organise files; sharing needs your word |
| Docs, Sheets, Slides | full | read, create and edit |
| Tasks | full | list, create, update and complete tasks |
| Contacts | readonly | look people up |

A change of levels changes what is asked for at the next sign-in. A grant already given does not
shrink by itself: sign out and in again, and Google shows the shorter list on the consent screen.

## The way out

`troi-console/google.sh signout you@gmail.com` revokes the sign-in at Google and sets the token file
aside as `<email>.json.revoked-<date>` in `data/google/credentials/`; nothing is deleted. You can also
revoke it yourself at [myaccount.google.com/permissions](https://myaccount.google.com/permissions),
under the app's name. Either way Troi's Google tools answer that they need a sign-in until you sign
in again.

## Checking it works

Reads first, one per service: "what came in today" (Gmail), "what is on my Google calendar this
week" (Calendar), "what changed in Drive lately" (Drive), "find the document called …" (Docs),
"which spreadsheets do I have" (Sheets), "find my pitch deck" (Slides), "show my task lists"
(Tasks). Then two harmless writes: "draft an email to me with the subject Troi test" (a draft in
your Gmail, never sent) and "add a task called Troi test" (in My Tasks). Both are yours to remove.

## If the tools are missing from a session

The tool server has to answer within the brain's start-up window. Installed as a uv tool it does
(about two seconds); resolved through `uvx` on every start it can be slower and needs the network,
which is how one session once began without its Google tools. `google.sh status` says which runner
is in use; `install.sh` installs the server.
