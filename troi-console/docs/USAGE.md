# Using Troi of Silo One

Written for someone who has installed it and wants to know what to say, click and do.

## Starting and stopping

- **Start**: double-click **Troi** on the Desktop, or type `troi` in a terminal. Everything comes up: the console (http://localhost:3100), the agent's server (http://127.0.0.1:8796), the face, the hands board, the eyes, the agent's browser and the voice line. Starting it twice is safe; the new launch replaces the old one.
- **Stop**: Ctrl-C in that window, or close it. The globe dims to "off". The four background services keep running: the pulse, the globe, the Telegram bridge and the nightly backup (`python3 troi-console/setup.py services status`).
- **Typing**: the Conversation page takes typed turns in the same session as your voice. For a terminal session, `cd ~/troi-of-silo-one && claude` gives you the same boot file and the same memory.

## The welcome

The first time the console opens, it goes to `/welcome`: who Troi is, in seven scenes, then the setup one step at a time.

- **You**: your name, the greeting, and what it calls you.
- **This Mac**: the permissions, a test of the talk key (it shows the words it heard), and the folders it may organise.
- **Memory**: a new vault or the one you have, and where the nightly backup goes.
- **Voice**: Kokoro, or ElevenLabs with your key and one of your voices.
- **Your phone**: Telegram.
- **Security**: the PIN, your face and your voice.
- **Extras**: keys for pictures and calls.

Your name and a memory are needed; everything else can wait. Until you finish, Troi hears but does not answer. The last step restarts the voice with everything you set, and Troi introduces itself.

`/welcome?step=setup` runs the setup again. Once you have been welcomed, changes there need the console unlocked with your PIN.

## The globe

A small gold globe floats on every Space and over full-screen apps: a wireframe sphere on a tilted axis, with an orbit ring and two satellites. It turns with the agent's state: slow when idle, fast when thinking, pulsing when speaking. Drag it to move it, and **double-click** it to open the console. A red badge counts what is waiting on you: approvals, plus reminders due in the next ten minutes (overdue ones too). The menu bar **T** shows or hides it, opens the console, or quits it.

## The voice

Kokoro speaks by default, local and free. **ElevenLabs** is the premium voice:

1. Keep your key in the Keychain: the welcome does it, or `troi-console/keychain.py set elevenlabs`.
2. In **Modes**, the Voice switch then offers ElevenLabs, with an **ElevenLabs voice** picker (and a reload button) listing your voices. Picking one switches to it at once. With no pick, your own cloned voice comes first, else the first listed.

From a terminal or by voice: `console.sh voice list`, `console.sh voice elevenlabs "Rachel"`, `console.sh voice kokoro`. The change applies from the next reply, and Kokoro takes over the moment ElevenLabs cannot answer. The same key powers meeting transcription (`meeting.py`).

## Talking

- Hold **Right Option**, speak, release. That key is never gated by Voice ID, so it always works.
- **Hands-free** listens all the time. With the wake word on, say the name first: "Troi, what time is it". Words before the name are dropped, so a TV in the room does not trigger it.
- **Voice ID** (Only me) fails closed. A clip that cannot be identified as you is dropped, whether it is too short, too different or unreadable, and the transcript shows why, with its score. The talk key is never gated.
- **Stopping a reply**: say "**stop**", or press **Stop** (the square button) or **Esc** in the console. With barge-in on, only a sentence with the agent's name interrupts.
- **Long jobs**: the agent says so instead of going quiet, and gives a short update if it is still busy after a while. It ignores its own voice.

## The console

The console is a web app at http://localhost:3100. Behind the pages is space: the Earth from low orbit, turning slowly, with a spacecraft whose engines light while the agent works. One control floats over everything: **the bar**, at the bottom centre.

- **The bar** shows the agent's name and state, with a small audio wave: its voice while it speaks, a breath while it listens. It holds:
  - the five **views**, which fill the whole window: the Face, the Hands board, the Files galaxy, the Apps galaxy and the Vault;
  - the **pages**: Conversation, Library, Modes, Routines, Reports, Approvals (with a count of what is waiting), Eyes, Browser and Agents (with a count of the agents at work);
  - then the bell, the lock and the light/dark switch.
- **Conversation**: everything the agent hears and says, live.
  - A reply grows word by word, straight on the page, then settles into the finished text with a copy button and the time under it; your own lines are bubbles on the right, with your initials and the time in the corner.
  - While the agent works, one line shows the tool in its hands and what it is on (the command, the file, the search, the page), each step taking the last one's place; when the reply comes the line settles into a count of the steps, opened with a click.
  - Faint "ignored" lines show what the filters dropped and why: a rejected voice shows its similarity score, and a line with no wake word says so.
  - Type and press Enter; a typed turn is answered here and out loud. Charts, tables, pictures and players the agent draws appear right in the conversation.
  - The composer is one card on the desktop: the + menu adds files or photos, takes a screenshot of the Mac or points at a file with @; a photo attached shows as its thumbnail, a file as a small card; the microphone and the send arrow stand on the right, the arrow becoming Stop while a reply is under way. The eraser in the header clears the page (a reload stays clear; the record and the session stay).
  - A reply of several sentences is one reply, rendered as Markdown (headings, lists, tables, code, links) when the agent shapes it so; the voice reads the words, never the marks.
  - Point it at a file: type `@` and pick one from your folders, or attach one with the clip (drop it on the composer, or paste it). Spreadsheets, documents, pictures and PDFs all work: the agent reads the file before it answers, with `read.py` for what its Read tool cannot open. Attached files are kept in `data/blobs/uploads/`.
  - It comes in two shapes, switched with the icon on its header, and your choice is remembered. The **column** is the Conversation page itself. The **floating** pane follows you onto every other page: drag it by the grip above its header, resize it from its corner, and double-click the grip to put it back.
- **Modes**:
  | Switch | Options |
  |---|---|
  | Permissions | Ask first / Auto-approve (two clicks to confirm) |
  | Microphone | Push to talk (hold Right Option) / Hands-free |
  | Wake word | In hands-free, only sentences containing the agent's name are acted on |
  | Model | Fast / Deep (Deep lasts for this session). Effort: Low to Max |
  | Eyes | Off / Every reply / Watch / Screen |
  | Voice ID | Off / Only me / Learn my voice (about a minute of push-to-talk speech) |
  | Strictness | How closely a voice must match your voice print. Move it right if someone else gets through, left if it starts ignoring you |
  | Face ID | Learn my face |
  | Voice | Kokoro / ElevenLabs, and which of your ElevenLabs voices |

  A protected choice needs the console unlocked. For Auto-approve and Hands-free, the page asks you to unlock and pick again. The other protected switches are filed for your approval on Telegram.
- **Library**: every picture the agent took, made, found or received, shelved as books by source and by day. You can:
  - filter by source and search;
  - open a book and view a picture full size (←/→ to move, Esc to close);
  - star the ones to keep past the 14-day tidy-up.
- **Routines**: everything that runs on a clock, with its last run:
  - the morning brief and the end-of-day report, each with a time and a switch;
  - the CI watch, the server watch and the calendar;
  - the vault backup, housekeeping and session compaction;
  - the Telegram bridge and the globe.

  **Run now** is there for the report, the brief, compaction, the backup, housekeeping and CI. Below them are the reminders, with Cancel.
- **Reports**: the end-of-day reports, each shown as it is, with its PDF, and a button that builds today's now.
- **Approvals**: cards for trash, force-quit, risky-click and protected-setting requests, and a record of earlier decisions. Approving needs the console unlocked (your PIN at the lock, or **Check it's me** on the Eyes page); rejecting never does. Requests wait across a restart, except risky clicks, which expire because the screen has moved on.
- **Eyes**: what the agent sees, the modes, the hands switch and face ID (see below).
- **Browser**: the agent's browser, mirrored live: Arc when it is installed (the same Arc you use), otherwise a Chrome of the agent's own. Watch it work, or take over: click, scroll, type, use the address bar, log in to a site for it. **Window** brings the real browser window forward.
- **Agents**: who the brain has put on a task, as a chart: the brain at the top, its agents below, each named for its job by the brain ("Scout: the Commuza notes", "Reviewer: PR 12"), the live ones ringed. Tap one for its task, what it is doing now, its last words and its report. Nothing there is a control: the brain decides whom to send. "Open the agents" brings it up.
- **Notifications**: the bell in the bar turns on the system's own notifications. Approvals and reminders always notify; a reply or a Telegram message notifies only while the console is not the page you are looking at.
- **Sound cues**: short interface sounds (made with ElevenLabs sound effects, in `troi-console/assets/`) play for a new approval, a due reminder, and a Telegram message while you are elsewhere. Turn them off with `"cues": false` in `data/console.json`; movie mode silences them for you.

The agent can drive all of it: "switch to the hands", "open my files", "open the vault", "open the modes", "show me the browser", "float the conversation", "tidy up". It does this with `console.sh`, whose commands the console follows on whichever page is open.

### On your phone

Open the same address on your phone, on the same network (`http://<your Mac's name>.local:3100`), and the console lays itself out as an app:

- a bar at the top: the agent's name and state, the page's title, and the lock (the PIN opens in a sheet);
- five tabs at the bottom: **Talk**, **Views**, **Library**, **Approvals** (with its count) and **More**;
- **More** holds everything else, one tap away: Modes, Routines, Reports, Eyes, Browser, notifications, appearance (auto, light, dark), the lock, and the welcome;
- the five views open full screen from **Views**, with a pill at the bottom to come back. In the galaxies: tap a star, drag it onto a folder, press and hold for the menu, pinch to zoom;
- the conversation is its own tab, with a messenger's composer: the field grows with the lines, and while it is empty a microphone stands where the send button will be. A voice note goes to the agent's own ears on the Mac and comes back as your line (it needs an https address: see below). The floating pane is a desktop shape and does not exist here. "Float the conversation" simply opens the Talk tab.

In Safari, **Share › Add to Home Screen** installs it with its own icon and no browser chrome. A phone held sideways keeps the same layout; an iPad gets the desktop console, with the lock opening the PIN sheet. Nothing is missing on the phone: every page and every switch of the desktop console is here.

**Reaching Troi from the phone is off until you turn it on.** The agent answers only on the Mac itself by default. Modes › *Your phone* offers two ways beyond that, both protected changes (your PIN), both taking effect at Troi's next start. **Tailscale** (the option appears when Tailscale is installed on the Mac): with Tailscale on the Mac and the phone, signed in to the same account, open `http://<the Mac's Tailscale address>:3100` on the phone (the hint under the switch shows it; the Mac's `.ts.net` name does not work in a browser, which insists on https for it); it works from anywhere, only your own devices can reach it, and every other network is turned away before a byte is read. **This network**: `http://<your Mac's name>.local:3100` on the same Wi-Fi, only on a network you trust, since anyone on it can then talk to Troi and read its record. The Face and Hands views also need their own servers reachable, which they are not yet; the galaxies, the conversation and every page work. **Https** (for the phone's microphone, and for the Mac's `.ts.net` name): enable HTTPS Certificates and Serve in Tailscale's admin console, then `Tailscale serve --bg --https=443 http://127.0.0.1:3100` and `Tailscale serve --bg --https=8796 http://127.0.0.1:8796` on the Mac; `https://<the Mac's tailnet name>/` then opens the console with the microphone working (the agent's server then keeps to the Mac itself and Tailscale carries the phone; the plain `http://<address>:3100` way stops working).

## The greeting

The voice line says your greeting ("Hello \<you\>.", as you set it in the welcome) the moment it starts. Once the brain is warm, it is handed a session-start line with the time, today's reminders and the top of your priorities. It then adds what a fellow person would add: a word on the time of day or the day ahead, a dry remark, or a small joke now and then. It is never the same line twice and it is not scripted. Turn it off with `"living_greeting": false` in `data/console.json`.

## The record (SQLite)

Everything the voice line logs is tailed into `data/troi.db`: the conversation per session, the cards the tools showed, approvals and what became of them, pictures, reports and routine runs. The console loads the last lines from it when it opens, so a reload keeps the conversation.

- `troi-console/db.py tail 50`, `db.py sessions` and `db.py stats` read it.
- `db.py star <path>` keeps a capture past the 14-day tidy-up.
- The server serves `/history`, `/sessions` and `/approvals`.

## Drawing in the conversation

Charts, tables, stats, galleries, tabs, maps and players are drawn inside the conversation from data. The agent runs `show.py` with a component tree (or `show.py chart …` / `show.py table …`), and the card lands in the log, live, and stays in the record. No HTML files, no screenshots of them. `show.py vocabulary` lists the components.

## AG-UI

The agent's server speaks [AG-UI](https://docs.ag-ui.com). `POST /agent` takes a `RunAgentInput`: the last user message is the line, and `forwardedProps.silent: true` makes it a written turn, answered but not spoken. It streams the standard events over SSE:

- the reply as it grows, and the tool in use;
- `silo.state`, `silo.partial` and `silo.note`;
- cards: `silo.pictures`, `silo.headlines` and `silo.ui`;
- `silo.approval` when something waits for you.

`GET /events` is the same vocabulary as a running feed of the whole conversation, and `POST /ask` runs one turn and returns the reply. Any AG-UI client can drive the agent with it; the console is one.

## The end-of-day report

At the report time (18:30 by default; set it in Routines or as `report_time` in `data/console.json`), the pulse builds a report of the day:

- commits in the git repositories under your file roots, and in the GitHub orgs and users the CI watch follows (who, what, when);
- CI runs, notes changed in the vault, files touched and reminders that fired;
- a "What changed today" paragraph, written by the agent from those facts in the same shared session.

It is saved as HTML and PDF under `data/blobs/reports/`, the PDF is sent to you on Telegram, and the Reports page lists every report. Ask for it any time ("send me today's report") or run `report.py`: `--date` for another day, `--no-send` to keep it local, `--no-narrative` to skip the paragraph.

## Things to ask for

| Say | What happens |
|---|---|
| "show me my files" / "open \<folder\> in the galaxy" / "where is \<project\>" | the Files galaxy opens, and the item lights up |
| "open the apps" / "open Spotify" / "close Chrome" / "what's running" | the Apps galaxy, or the app is opened, focused or politely quit |
| "look at me" / "what am I holding" | one camera photo, described |
| "what's on my screen" / "read this error" | a screenshot, read |
| "remind me in 20 minutes to ..." / "remind me at 3pm ..." | the pulse fires it, and the agent says it (on Telegram when the voice line is down) |
| "review PR 3 on my-app" / "review my changes in the website" | a review in a headless session of the agent's own, in a throwaway checkout with read-only tools, following your Code Review job. The report lands in `data/blobs/reviews/` and on Telegram, and goes on the PR only when you say "post it" |
| "work on the website" / "open the my-app project" | a Terminal window with a Claude Code session inside that project folder that is still your agent (the boot file, the guard and the vault come along); `code.sh list` shows the projects from the settings |
| "how are the servers" / "check prod" | a read-only health check over SSH of every server in `data/servers.json`: load, disk, memory, failed services, containers, updates, reboot needed. The pulse runs it every 15 minutes and speaks only what changed. A node that wants your own sign-in (a Google Cloud VM behind IAP with OS Login's 2-step, or gcloud signed out) shows as signed out, not down: the agent asks you once to sign in from your terminal, sets itself a reminder and picks the task up again later |
| "what's on today" / "when is my next meeting" | the Mac's Calendar app (add Google or others under Internet Accounts). The pulse gives a heads-up 15 minutes before an event, the morning brief lists the day, and "record this meeting" names the recording after the event |
| "play some jazz" / "play my gospel playlist" / "pause" / "next" / "what's this song" / "louder" | Apple Music: a playlist by name, then the library by genre, artist, album or title. When nothing matches, the app's search opens for you to tap. With `duck_music` on in the settings, music dips while the agent speaks |
| "movie mode" / "movie mode off" | push to talk so the film can't wake the agent, sound cues off, the floating conversation hidden and the page dimmed. "Off" restores it (say "go hands free" yourself if you were hands-free) |
| "record this meeting" / "stop recording" / "transcribe it" | a recording, from "Meeting In" (the Mac's microphone plus BlackHole, with the Mac's sound routed through "Meeting Out" until stop), or from the microphone alone without BlackHole. Then a speaker-labelled transcript with ElevenLabs Scribe in `data/blobs/meetings/`, from which the agent writes the meeting note into the vault |
| "good morning" | the morning brief |
| "how is CI" / "any failed builds" | CI status across the GitHub orgs and users you watch (set under Routines › CI watch) |
| "back up now" | the nightly backup, now: the vault, then the record |
| "call me" | a call link on Telegram; the agent answers |
| "show me the photo of ..." | the picture goes up on the hands board |
| "move X into Y" / "rename" / "make a folder" | done directly, inside your file roots (never overwrites) |
| "delete X" / "trash X" | an approval card. Nothing moves until you approve it (the console unlocked, or "approve" on Telegram), and then it goes to the macOS Trash |
| "click the Save button" / "type hello in that field" / "open the View menu and switch to list" | the native hands: the control is found by name in the app's accessibility tree, pressed, and the result read back; risky labels ask for approval. The guarded cursor remains for what has no name |
| "draw me a…" / "make a picture of…" | a picture, in the Library and on the board |
| "research …" / "show me what … looks like" | credited pictures on the board while it talks |
| "what's in the news" / "what does NTV say about…" | headlines per outlet, Uganda first, read out or on the board |
| "go hands free" / "stop asking for permission" / "clear the session" | only in your verified voice (or your face), from an unlocked console, or with your approve on Telegram |
| "open example.com and fill in the form" | the agent's browser |
| "what's in my inbox from the bank" / "draft a reply to Sarah" / "find the budget sheet in Drive" / "put the launch on my Google calendar" | your Google account (Calendar, Gmail, Drive, Docs, Sheets, Tasks, Contacts), once signed in (`google.sh signin`); sending, sharing and answering invitations wait for your go-ahead, and nothing there is ever deleted |

## The Files galaxy

A folder drawn as a galaxy. Folders are glowing nuclei, and files are stars, coloured and marked by type. Solid lines are the folder tree; dashed lines join related files (the same name with different extensions, wikilinks, links inside Markdown).

- **Moving around.** Click a folder to unfold it; double-click it to make it the centre. Breadcrumbs go up. The search box finds a file by name. Wheel to zoom; Shift-drag rotates, Alt-drag tilts, and `0` resets. In the Vault view a minimap shows where you are.
- **Peeking.** Double-click a file to peek at it in the drawer, a small window of its own inside the galaxy (drag it, resize it, or minimise it to a chip under the Hands button). It shows rendered Markdown, highlighted code, Word, Excel, CSV as a table, JSON, PDF, audio, video, 3D models and images.
  - **Edit** and **Save** text files. The previous version is kept in `data/backups/`, and goes to the Trash after 30 days.
  - **Open in app** opens the file in its application.
  - **Ask \<Agent\>** sends it to the agent.
- **Changing things.** Right-click or long-press for rename, new folder, reveal in Finder, move to Trash (an approval) or let it float. Drag a file onto a folder to move it; a menu confirms and offers to copy instead. Drag a star aside to pin it where you work.
- **Recent** (the button next to Hands) shows files changed in the last seven days. The view refreshes itself when files change.
- **Memory graph** draws the vault's notes and their wikilinks.

The root of the Files galaxy is called Silo One.

## The Vault

The vault is your agent's memory. The Vault view shows it as a wall of cards drawn by the same engine as the galaxies, so every gesture is the same.

- Folders sit across the top as small stacks, each with the opening lines of its index note, its counts and its newest notes.
- Notes sit below, with their opening lines, word and link counts, age and tags.
- Tap a folder to open it, and tap a note to read it in the drawer (rendered Markdown, editable).
- Drag a note onto a folder to move it. Right-click for rename, new folder, reveal, or a trash request.
- Search lights up matches in titles, excerpts and tags. **Memory graph** draws the notes and their wikilinks instead.

## The Apps galaxy

Every application as a standalone icon, grouped by category; running apps glow. Tap (or dwell with a hand) to open one. A long press offers Open or Bring to front, Quit, Force quit (an approval) and Show in Finder.

## Hand gestures (webcam)

The webcam is off until you ask, to save the battery. The **Hands** switch on the Eyes page, or "hands on" to the agent, turns hand tracking on for the hands board and the galaxies; the Hands button in the corner of the board, and the one inside a galaxy, do the same and keep the console's switch in step. Chrome asks for the camera the first time.

| Hand | Meaning |
|---|---|
| One finger (index) | the cursor. Hover a star or a card to focus it; hold still for a moment (dwell) to open it |
| A pinch (thumb and index), or index and middle fingers together | grab and drag; a long pinch opens the menu |
| Fist | the cursor hides and anything held is dropped |
| A pinched hand rolled, on empty space | rotate the galaxy |
| Two pinched hands apart or together | zoom (turning them rotates, moving them up and down tilts) |
| In a peek drawer: hand up and down | scrolls like a trackpad (small movements, repeat) |
| In a peek drawer: swipe right | closes it |

The galaxies' sensitivity lives in `data/console.json` under `hands` (pinch thresholds, dwell time, magnet), or use `console.sh hands <key> <value>`. Press **P** in a galaxy to sample a pose. The mouse also works as a hand on the hands board: move is an open hand, hold is a pinch, click is a tap.

## Telegram

Text, photos and voice notes both ways, in the same session as the console.

- **Replies.** The agent answers in plain text, and adds a voice note (in Kokoro) when you sent one; `"voice_replies": true` in the settings sends a voice note with every reply.
- **Approvals.** Send "approve" or "reject" (or /approve) to decide the newest request that is waiting.
- **Calls.** `/call` starts a voice call.
- **The agent writing first.** It messages you when something needs you while the voice line is down: a reminder, a failed build, a server change. It never sends more than one message for one event.

## Voice calls

"Call me" or `/call` sends a link. Open it on your phone, tap to allow the microphone (or switch to push to talk), and talk. The agent answers in Kokoro and stays in the same conversation; with a voice print it listens for your voice (it lets short clips through). Hang up to end.

A phone allows its microphone only on an https page, so calls need `call.html` (in `console/public/`) hosted on an https address and set as `call_page` in `data/console.json`. The console serves the page on your own network too, but over plain http, and phones refuse the microphone there.

## Safety

- **The agent cannot delete.** A hook blocks every destructive command, whatever the permission mode. Trash, force-quit and risky clicks need your approval, and only you can give it: the console unlocked with your PIN or face, or your own Telegram chat. What you approve for removal goes to the macOS Trash. The nightly housekeeping also only uses the Trash, for old captures, old editor backups and old logs.
- **The agent cannot reach its own safeguards.** That covers your secrets in the Keychain, approvals and unlocks, the settings file, your voice and face prints, its record, its boot file, Claude Code's settings and the guard's code. The same hook blocks any attempt.
- **The hands** press controls by name through the accessibility tree and never write into password fields; a control labelled delete, pay, send, submit, install and the like is not pressed: an approval is filed for you. The guarded cursor, for what has no name, additionally refuses to click without a fresh screenshot.
- **The browser.** With Arc installed, the agent drives your Arc: Arc runs one instance only, so it cannot keep a separate one, and it starts yours, on your own profile, with its debugging port. Your logins are in it, which is exactly why payments, deletions and messages from a site need your explicit go-ahead in the same turn. Without Arc, the agent's browser is a Chrome of its own with none of your logins unless you log in for it on the Browser page.
- **What leaves the Mac.** Photos and screenshots stay on the Mac and go only to your private nightly backup. Your voice and face prints never leave it, and secrets stay in the Keychain.

## Protected settings and the PIN

Some switches lower the agent's guard. Anyone in the room could otherwise say "go hands free" or "stop asking for permission", so each needs you:

- **Spoken or typed phrases** (auto-approve, hands-free listening, clearing the session) go through in your verified voice. If the voice does not match and your face is learnt, the camera gets a look before the order is refused. They also go through from an unlocked console, or with your approve on Telegram.
- **Settings** (voice ID off, looser or learning, the wake word off, the camera or screen sight on, learning a face, the face gate off, and the guard itself) change only from an unlocked console or with your approve on Telegram.

To unlock, set a PIN once (the welcome does it, or `troi-console/keychain.py set pin`), then type it at the lock in the bar, or use **Check it's me** on the Eyes page. The console stays unlocked for 15 minutes: protected switches apply straight away, and approvals go through.

Anything protected that arrives another way, including the agent being talked into it, becomes an approval card and a Telegram message. The guard is on by default (`guard_settings` in the settings), and turning it off is itself protected. Five wrong PINs lock the console for ten minutes. Until something can verify you (a PIN, a paired phone, or a voice or face print), the guard stands down; the doctor warns about it.

## Eyes, screen sight and Face ID

The **Eyes** page shows what the agent sees: the live frame while the camera is on, or the look you just took. **Look now** takes a photo and **Screen now** a screenshot. The mode switch is the same as in Modes:

- **Off.**
- **Every reply**: a fresh camera frame with each request.
- **Watch**: it speaks up when the room changes.
- **Screen**: a screenshot with every request, so it answers knowing what is on your screen. Screen sight needs the Screen Recording permission for Terminal.

**Face ID** is another way to prove it is you, beside the voice print, the PIN and Telegram. It uses a real face-recognition model in its own environment, and nothing leaves the Mac. Learn your face once in Modes › Face ID › Learn my face: five photos, a second apart. It is a protected change, so it needs the console unlocked or a Telegram approve. From then on:

- **Check it's me** on the Eyes page unlocks the console like the PIN does.
- When someone gives a protected spoken order in a voice that does not match yours, the agent says "One moment, let me see you" and checks the camera before refusing.

A photo held up to the camera can fool it; the PIN cannot, so keep the PIN for the things that matter most.

**The face gate** (`face_gate` in the settings, `console.sh face-gate on|off`) makes hands-free with the wake word answer only while your face is at the camera, so the TV can't wake the agent. It needs a learnt face, it fails closed, the talk key always works, and turning it off is protected.

## The news, Uganda first

"What's in the news", "what's trending in Uganda", "what does NBS say about the budget": the agent reads the outlets listed in `troi-console/news.json`. Out of the box:

- **Uganda:** NBS Television, Nile Post (Next Media), NTV Uganda, UBC, Galaxy FM, Simba FM, The Independent, The Observer, PML Daily, and Google News for Uganda.
- **World:** BBC World, BBC Africa, Al Jazeera, The Guardian and The Washington Post.

It can:

- give the latest per outlet, with how old each story is;
- put a front page of cards on the board;
- search every outlet for a subject;
- read an article out;
- list an outlet's latest YouTube videos;
- open its X or Facebook page in its browser when you ask what they are posting.

Outlets without a working website (UBC, Simba FM) are covered through Google News and YouTube. Edit `news.json` to add or drop outlets; feeds, Google News queries and handles are all it needs.

## Research with pictures

When the agent researches or explains something that has a look to it, it puts pictures up while it talks: free, credited pictures from Wikimedia Commons, Wikipedia and Openverse, the pictures a web page leads with, or a screenshot of the page.

- **On the board**, they land as a numbered grid under one caption card. Each new topic sweeps the last unless the agent is asked to add.
- **Steering**: say "focus on the second one" to spotlight a picture, and "show them all" to bring the rest back.
- **Kept**: they also land in the Library under Research, and in `data/blobs/research/<topic>/` with a credits file.
- **To your phone**: "Send me those."

The board has a calm dark backdrop, its camera stays off until hand tracking is on, and pictures keep their true colours.

## Making pictures

"Draw me a…", "make a picture of…", "imagine…": the agent makes a picture from words, or restyles one you point it at, saves it in the Library, and can put it on the hands board. It needs an image key in the Keychain; the welcome's Extras step keeps it, or:

```bash
troi-console/keychain.py set openai     # OpenAI
troi-console/keychain.py set gemini     # Google Gemini
```

`troi-console/imagine.py check` says which backend is on. Pictures and their prompts land in `data/blobs/imagined/`.

## Housekeeping

At 03:00 the pulse runs `housekeeping.sh`:

- logs that pass about 20 MB are rotated, and rotated logs go to the Trash after a week;
- camera looks, screenshots and Telegram files older than 14 days go to the Trash, unless starred (their record stays);
- editor backups go to the Trash after 30 days.

At 03:30 it compacts the shared session. `doctor.sh` is the check-up, `tools.sh` prints the agent's full toolbox, and `housekeeping.sh` runs the cleanup now.
