---
title: Your Google account
description: "Calendar, Gmail, Drive, Docs, Sheets, Tasks and Contacts, through the Google Workspace tool server: what Troi may do there, and the one-time way in."
order: 13
---

Troi can work in your Google account: read and search your mail and draft replies, read and create
calendar events, find and read files in Drive, read and write Docs and Sheets, keep Tasks, look up
Contacts. The tools come from the Google Workspace MCP server, run as one of the brain's tool
servers (`troi-console/google.sh mcp`), signed in as you, once.

## What it may do

- **Reading, searching, drafting and creating are Troi's**: "what's in my inbox from the bank",
  "draft a reply to Sarah", "put the launch on my Google calendar on the first at nine", "find the
  budget sheet in Drive and read the totals", "add a task for Monday".
- **Sending an email, sharing a file or document, or answering an invitation needs your explicit
  go-ahead in the same turn.** The draft is the safe default: "the draft is in your Gmail".
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
| The APIs | Calendar, Gmail, Drive, Docs, Sheets, Tasks, People (`google.sh enable`) |

What you read and write there goes to Google as with any client; the mail and files Troi reads to
answer a question go to the model as part of the conversation, like a file it is pointed at.
