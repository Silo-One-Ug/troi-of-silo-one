# Using Troi of Silo One

Written for someone who has installed it and wants to know what to say, click and do.

## Starting and stopping

- **Start**: double-click **Troi** on the Desktop, or type `troi` in a terminal. Everything comes up: the console (http://localhost:3100), the agent's server (http://127.0.0.1:8796), the face, the hands board, the eyes, the agent's browser and the voice line. Starting it twice is safe; the new launch replaces the old one.
- **Stop**: Ctrl-C in that window, or close it. The four background services (ring, pulse, Telegram, backup) keep running; the ring dims to "off".
- **Typing**: the Conversation page takes typed turns in the same session as your voice. For a terminal session, `cd ~/troi-of-silo-one && claude`: same boot file, same memory.

## The globe

A small gold globe, a wireframe sphere on a tilted axis with an orbit ring and two satellites, floats on every Space and over full-screen apps. It turns with the agent's state (slow when idle, fast when thinking, pulsing when speaking). Drag it to move it. **Double-click** it to open the console. A red badge shows the number of things waiting on you (approvals, reminders due soon). The menu bar **T** shows, hides or quits it.

## The welcome
The first time the console opens it goes to `/welcome`: who Troi is, in seven scenes, then the setup one step at a time. The steps are you (your name, the greeting, what it calls you), this Mac (the permissions, the talk key, the folders it may organise), memory (a new vault or yours, and the nightly backup), the voice (Kokoro, or ElevenLabs with your key and one of your voices), your phone (Telegram), security (the PIN, your face and your voice) and the extras. The last step restarts the voice with everything you set, and Troi introduces itself. `/welcome?step=setup` runs the setup again; once you have been welcomed, changes there need the console unlocked with your PIN.

## The voice
Kokoro speaks by default, local and free. **ElevenLabs** is the premium voice: keep your key in the Keychain (the welcome does it, or `troi-console/keychain.py set elevenlabs`), then Modes › Voice › **Voices** lists yours; pick one and click **ElevenLabs** (with no pick, your own cloned voice comes first, else the first listed). From a terminal or by voice: `console.sh voice list`, `console.sh voice elevenlabs "Rachel"`, `console.sh voice kokoro`. The switch is live: the next sentence comes in the new voice, and Kokoro takes over the moment ElevenLabs cannot answer. The same key powers meeting transcription (`meeting.py`).

## The record (SQLite)
Everything the voice line logs is tailed into `data/troi.db` (stdlib SQLite): the conversation per session, cards the tools showed, approvals and what became of them, pictures the agent found, reports and routine runs. The console loads the last lines from it when it opens, so a reload keeps the conversation. `troi-console/db.py tail 50`, `db.py sessions`, `db.py stats`; the server serves `/history`, `/sessions`, `/approvals`.

The conversation has two shapes: a full column on the right, or a floating pane you drag where you like. The button on its header switches (**Column** / **Floating**) and the choice is remembered.

## Drawing in the conversation
Charts, tables, stats, galleries, tabs, maps and players are drawn inside the conversation from data: the agent runs `show.py` with a component tree (or `show.py chart …` / `show.py table …`), the card lands in the log, live, and stays in the record. No HTML files, no screenshots of them. `show.py vocabulary` lists the components; the console draws them with its own components.

## AG-UI
The console server speaks [AG-UI](https://docs.ag-ui.com): `POST /agent` takes a `RunAgentInput` (the last user message is the line; `forwardedProps.silent: true` makes it a written turn, answered but not spoken) and streams the standard events over SSE: the reply as it grows, the tool in use, `silo.state`, `silo.pictures` and `silo.headlines` cards, `silo.approval` when something waits for you. `GET /events` is the same vocabulary as a running feed of the whole conversation. Any AG-UI client can drive the agent with it; the console is one.

## The console

The console is a web app at http://localhost:3100. Behind everything is space: the Earth from low orbit, turning slowly. One control floats over it: **the bar**, at the bottom centre. Nothing else is fixed, and nothing sits behind the bar.

- **The bar** shows the agent's name and state with a small audio wave: its voice while it speaks, a breath while it listens. It holds the five **views**, which fill the window: the Face, the Hands board, the Files galaxy, the Apps galaxy and the Vault. It also holds the **pages**: Conversation, Library, Modes, Routines, Reports, Approvals (with a count of what is waiting), Eyes and Browser. Then come the bell, the lock and the light/dark switch.
- **Conversation**: everything the agent hears and says, live. A reply appears word by word while the agent is still producing it, then settles into the finished text. Faint "ignored" lines show what the filters dropped and why (a rejected voice shows its similarity score). Type and press Enter; **Stop** or Esc cuts a reply off. Charts, tables, pictures and players the agent draws appear right in the conversation. It comes in two shapes: a full **column**, or a **floating** pane you drag by its header and resize from its corner, which stays inside the window and above the bar. The switch is on its header, and the choice and the pane's place are remembered.
- **Modes**:
  | Switch | Options |
  |---|---|
  | Permissions | Ask first / Auto-approve (two clicks to confirm) |
  | Microphone | Push to talk (hold Right Option) / Hands-free |
  | Wake word | In hands-free, only sentences containing the agent's name are acted on |
  | Model | Fast / Deep. Effort: Low to Max |
  | Eyes | Off / Every reply / Watch / Screen |
  | Voice ID | Off / Only me / Learn my voice (about a minute of push-to-talk speech) |
  | Strictness | How closely a voice must match your voice print. Move it right if someone else gets through, left if it starts ignoring you |
  | Face ID | Learn my face |
  | Voice | Kokoro / ElevenLabs, and which of your ElevenLabs voices |

  A protected change (see below) needs your PIN; the page says so and files it for your approval.
- **Library**: every picture the agent took, made, found or received, shelved as books by where it came from and by day. Search, open a book, view a picture full size, and star the ones to keep past the 14-day tidy-up.
- **Routines**: everything that runs on a clock, with its time, its switch and its last run: the morning brief, the end-of-day report, the CI watch, the vault backup, housekeeping, session compaction, the Telegram bridge and the globe. Change a time, switch a job off, or run one now. Below them, the reminders, with Cancel.
- **Reports**: the end-of-day reports, each shown as it is, with its PDF.
- **Approvals**: cards for trash, force-quit, risky-click and protected-setting requests, and a record of earlier decisions. Approving needs the console unlocked (your PIN at the lock, or **Check it's me** on the Eyes page); rejecting never does.
- **Eyes**: what the agent sees, with the modes, the hands switch and face ID (see below).
- **Browser**: the agent's own Chrome, mirrored live. Watch it work, or take over: click, scroll, type, use the address bar, log in to a site for it. **Window** brings the real Chrome window forward.
- **The face gate** (`face_gate` in the settings, `console.sh face-gate on|off`): hands-free only answers while your face is at the camera, so the TV can't wake the agent. It needs a learnt face (Modes › Face ID). It fails closed, the talk key always works, and turning it off is protected.
- **Notifications**: the bell in the bar turns on the system's own notifications. Approvals and reminders always notify; a reply or a Telegram message only while the console is not the page you are looking at.
- **Sound cues**: short interface sounds (made with ElevenLabs sound effects, in `troi-console/assets/`) play for a new approval, a due reminder, and a Telegram message while you are elsewhere. Switch them off with `"cues": false` in `data/console.json`; movie mode silences them for you.

The agent can drive all of it: "switch to the hands", "open my files", "open the vault", "open the modes", "show me the browser", "float the conversation", "tidy up". It does this with `console.sh`, whose commands the console follows on whichever page is open.

## The greeting

The voice line says your greeting ("Hello \<you\>.", as you set it in the welcome) the moment it starts. Once the brain is warm it is handed a session-start line with the time, today's reminders and the top of your priorities, and it adds what a fellow person would add: a word on the time of day, the shape of the day, a dry remark or a small joke now and then. It is never the same line twice and it is not scripted. Turn it off with `"living_greeting": false` in `data/console.json`.

## The end-of-day report

At the report time (default 18:30, in Routines or `report_time` in `data/console.json`) the pulse builds a report of the day: every commit in every git repository under your browsable folders (who, what, when), commits and CI runs in your GitHub org, notes changed in the vault, files touched, reminders that fired, and a "What changed today" paragraph written by the agent from those facts, in the same shared session. It is saved as HTML and PDF under `data/blobs/reports/`, the PDF is sent to you on Telegram, and the Routines pane lists every report with a download. Ask for it any time ("send me today's report") or run `report.py`, with `--date` for another day and `--no-send` to keep it local.

## Talking

- Hold **Right Option**, speak, release. That key is never gated by Voice ID, so it always works.
- **Hands-free** listens all the time. With the wake word on, say the name first: "Troi, what time is it". Words before the name are dropped, so a TV in the room does not trigger it.
- **Voice ID** (Only me) fails closed: a clip that cannot be identified as you, whether too short, too different or unreadable, is dropped, and the transcript shows why with its score. The talk key is never gated.
- Say "**stop**" to cut a reply off without starting a new one. With barge-in on, only a sentence with the agent's name interrupts.
- If the agent starts something long it says so instead of going quiet, and gives a short update if it is still busy after a while.

## Things to ask for

| Say | What happens |
|---|---|
| "show me my files" / "open \<folder\> in the galaxy" / "where is \<project\>" | the Files galaxy opens, the item lights up |
| "open the apps" / "open Spotify" / "close Chrome" / "what's running" | the Apps galaxy, or the app is opened, focused or politely quit |
| "look at me" / "what am I holding" | one camera photo, described |
| "what's on my screen" / "read this error" | a screenshot, read |
| "remind me in 20 minutes to ..." / "remind me at 3pm ..." | the pulse fires it, spoken and on Telegram |
| "review PR 3 on my-app" / "review my changes in the website" | a review by the agent in a headless session of its own, in a throwaway checkout with read-only tools, following your Code Review job; the report lands in `data/blobs/reviews/` and on Telegram, and goes on the PR only when you say "post it" |
| "work on the website" / "open the my-app project" | a Terminal window with a Claude Code session inside that project folder that is still your agent (boot file, deletion guard and vault come along); `code.sh list` shows the projects from the settings |
| "how are the servers" / "check prod" | a read-only health check over SSH of every server in `data/servers.json` (load, disk, memory, failed services, containers, updates, reboot needed); the pulse runs it every 15 minutes and speaks only what changed |
| "what's on today" / "when is my next meeting" | the Mac's Calendar app (add Google or others under Internet Accounts); the pulse warns 15 minutes before an event, the morning brief lists the day, and "record this meeting" names the recording after the event |
| "play some jazz" / "play my gospel playlist" / "pause" / "next" / "what's this song" / "louder" | Apple Music: a playlist by name, then the library by genre, artist, album or title; nothing in the library opens the app's search for you to tap. Music dips while the agent speaks (`duck_music`) |
| "movie mode" / "movie mode off" | push to talk so the film can't wake the agent, sound cues off, the console panel hidden and the page dimmed; "off" restores it (say "go hands free" yourself if you were hands-free) |
| "record this meeting" / "stop recording" / "transcribe it" | a recording (from "Meeting In", the Mac's microphone plus BlackHole, with the sound output routed through "Meeting Out" until stop; the microphone alone without BlackHole), then a speaker-labelled transcript with ElevenLabs Scribe in `data/blobs/meetings/`, from which the agent writes the meeting note into the vault |
| "good morning" | the morning brief |
| "how is CI" / "any failed builds" | CI status for your GitHub org |
| "back up the vault" | the nightly backup, now |
| "call me" | a call link on Telegram; the agent answers |
| "show me the photo of ..." | the picture goes up on the hands board |
| "move X into Y" / "rename" / "make a folder" | done directly (never overwrites) |
| "delete X" / "trash X" | an approval card. Nothing moves until you approve it (the console unlocked with your PIN, or Telegram) |
| "click the Save button" / "type hello in that field" | the guarded cursor: it looks first, refuses risky labels, asks for approval |
| "draw me a…" / "make a picture of…" | a picture, in the Library and on the board |
| "research …" / "show me what … looks like" | credited pictures on the board while it talks |
| "what's in the news" / "what does NTV say about…" | headlines per outlet, Uganda first, read out or on the board |
| "go hands free" / "stop asking for permission" | only in your verified voice, from an unlocked console, or with your approve on Telegram |
| "open example.com and fill in the form" | the Playwright browser |

## The Files galaxy

A folder drawn as a galaxy. Folders are glowing nuclei, files are stars coloured and iconed by type. Solid lines are the folder tree; dashed lines are related files (same name with different extensions, wikilinks, links inside Markdown).

- Click a folder to unfold it, double-click to make it the centre. Breadcrumbs go up.
- Double-click a file to peek in the drawer, which is a pane like the others (drag, resize, minimise to a chip under the Hands button): rendered Markdown, syntax-highlighted code, Word, Excel, CSV as a table, JSON, PDF, audio, video, 3D models, images. **Edit** and **Save** text files (the previous version is kept in `data/backups/`). **Open in app**. **Ask \<Agent\>** sends it to the agent.
- Right-click or long-press: rename, new folder, reveal in Finder, move to Trash (approval), let it float.
- Drag a file onto a folder to move it (a menu confirms). Drag a star aside to pin it where you work.
- Wheel to zoom. Shift-drag rotates, Alt-drag tilts, `0` resets. The minimap at the bottom shows where you are.
- The **Recent** strip shows files changed in the last seven days. The view refreshes itself when files change.
- **Memory graph** draws the vault's notes and their wikilinks.

The root of the Files galaxy is called Silo One.

## The Vault

The vault is your agent's memory, and the Vault view shows it as a wall of cards drawn by the same engine as the galaxies, so every gesture is the same. Folders sit across the top as small stacks, each with the opening lines of its index note, its counts and its newest notes; notes sit below with their opening lines, word and link counts, age and tags. Tap a folder to open it, tap a note to read it in the drawer (rendered Markdown, editable). Drag a note onto a folder to move it. Right-click for rename, new folder, reveal, or a trash request. Search lights up matches in titles, excerpts and tags. **Memory graph** draws the notes and their wikilinks instead.

## The Apps galaxy

Every application as a standalone icon, grouped by category. Running apps glow. Tap (or dwell with a hand) to open, long-press for quit or force quit (force quit asks for approval).

## Hand gestures (webcam)

The webcam is off until you ask, to save the battery: the **Hands** switch on the Eyes page (or "hands on" to the agent) turns hand tracking on for the board and the galaxies; the Hands button inside a galaxy does the same for that view. A small sampler shows what the tracker sees.

| Hand | Meaning |
|---|---|
| One finger (index) | the cursor. Hover a star or a card to focus it; hold still for a moment (dwell) to open it |
| Two fingers pinched | grab and drag |
| Fist | stop tracking (the cursor freezes) |
| Open hand rolled | rotate the galaxy |
| Two hands apart or together | zoom; move them up and down together to tilt |
| In a peek drawer: hand up and down | scrolls like a trackpad (small movements, repeat) |
| In a peek drawer: swipe right | closes it |

Sensitivity lives in `data/console.json` under `hand_tuning` (pinch thresholds, dwell time, magnet). The mouse also works as a hand on the hands board: move is an open hand, hold is a pinch, click is a tap.

## Telegram

Text, photos and voice notes both ways, in the same session as the console. The agent answers in plain text, or in its own voice when you send a voice note. Reply "approve" or "reject" to approval requests. `/call` starts a voice call. The agent can message you first when something is urgent (a failed build, a reminder while you are away).

## Voice calls

"Call me" or `/call` sends a link. Open it on your phone, tap to allow the microphone, talk. The agent hears with voice ID, answers with its voice, and stays in the same conversation. Hang up to end.

## Safety

- The agent cannot delete. Every destructive command is blocked by a hook regardless of permission mode. Trash, force-quit and risky clicks need your approval, and only you can give it: the console unlocked with your PIN or face, or your own Telegram chat.
- The agent cannot reach its own safeguards: your secrets in the Keychain, approvals and unlocks, the settings file, your voice and face prints, its record, its boot file, Claude Code's settings and the guard's code. The same hook blocks the attempt.
- The guarded cursor refuses to click without a fresh screenshot, never types into password fields, and files an approval for controls labelled delete, pay, send, submit, install and the like.
- The browser is the agent's own Chrome (its own profile), with none of your logins unless you log in for it on the Browser page. Payments, deletions and messages from a site need your explicit go-ahead in the same turn.
- Camera and screenshots stay on the machine. Voice ID is a local voice print. Secrets stay in the Keychain.

## Protected settings and the PIN

Some switches lower the agent's guard: auto-approve, hands-free listening, clearing the session, voice ID off or looser, the wake word off, the camera on, and the guard itself. Anyone in the room could otherwise say "go hands free" or "stop asking for permission", so these need one of three things:

- **Your verified voice, or your face.** With a voice print learnt, a spoken order is checked against it before it runs; if the voice does not match and your face is learnt, the camera gets a look before the order is refused.
- **An unlocked console.** Set a PIN once (the welcome does it, or `troi-console/keychain.py set pin`), then type it at the lock in the bar; the console stays unlocked for 15 minutes, protected switches apply straight away, and approvals go through.
- **Your approve on Telegram.** Anything protected that arrives another way, including the agent being talked into it, becomes an approval card and a Telegram message. Reply "approve" or "reject". On the console, approving any card needs the console unlocked.

The guard is on by default (`guard_settings` in the settings). Turning it off is itself protected. Five wrong PINs lock the console for ten minutes. If you have no voice print, no PIN and no Telegram yet, the doctor and the console say so: until then nothing can verify you, so the guard stands down.

## Eyes, screen sight and Face ID

The **Eyes** page shows what the agent sees: the live frame while the camera is on, or the last photo. **Look now** takes a photo, **Screen now** a screenshot, and the mode switch is the same as in Modes: Off, Every reply (a fresh camera frame with each request), Watch (it speaks up when the room changes), and **Screen**, which attaches a screenshot to every request so it answers knowing what is on your screen. Screen sight needs the Screen Recording permission for the terminal app.

**Face ID** is a second way to prove it is you, beside the voice print, the PIN and Telegram. It uses a real face-recognition model in its own environment; nothing leaves the Mac. Learn your face once (Modes > Face ID > Learn my face: five photos, a second apart; it is a protected change, so it needs the PIN, your voice or a Telegram approve). From then on **Check it's me** on the Eyes page unlocks the console like the PIN does, and when someone gives a protected spoken order in a voice that does not match yours, the agent says "One moment, let me see you" and checks the camera before refusing. A photo held up to the camera can fool it; the PIN cannot, so keep the PIN for the things that matter most.


## The news, Uganda first

"What's in the news", "what's trending in Uganda", "what does NBS say about the budget": the agent reads the outlets listed in `news.json`. Out of the box: NBS Television, Nile Post (Next Media), NTV Uganda, UBC, Galaxy FM, Simba FM, The Independent, The Observer, PML Daily and Google News for Uganda; then BBC World, BBC Africa, Al Jazeera, The Guardian and The Washington Post. It gives the latest per outlet with how old each story is, can put a front page of cards on the board, search every outlet for a subject, read an article out, list an outlet's latest YouTube videos, and open its X or Facebook page in its browser when you ask what they are posting. Outlets without a working website (UBC, Simba FM) are covered through Google News and YouTube. Edit `news.json` to add or drop outlets; feeds, Google News queries and handles are all it needs.

## Research with pictures

When the agent researches or explains something that has a look to it, it puts pictures up while it talks: free, credited pictures from Wikimedia Commons, Wikipedia and Openverse; the pictures a web page leads with; or a screenshot of the page. They land on the hands board as a numbered grid under one caption card (each new topic sweeps the last unless the agent is asked to add), and you can say "focus on the second one" to spotlight a picture and "show them all" to bring the rest back. They also land in the Library under Research, and in `data/blobs/research/<topic>/` with a credits file. "Send me those" sends them to your phone. The board itself now has a calm dark backdrop instead of the camera feed (the camera still runs for hand tracking), and pictures keep their true colours.

## Making pictures

"Draw me a…", "make a picture of…", "imagine…": the agent makes a picture from words, or restyles one you point it at, saves it in the Library, and can put it on the hands board. It needs an image key in the keychain, whichever you have:

```bash
troi-console/keychain.py set openai     # OpenAI
troi-console/keychain.py set gemini     # Google Gemini
```

The welcome's Extras step keeps them too.

`imagine.py check` says which backend is on. Pictures and their prompts land in `data/blobs/imagined/`.

## Housekeeping

The pulse rotates logs nightly, moves camera looks, screenshots and Telegram files older than 14 days to the Trash (starred ones stay; their record stays), and compacts the shared session at 03:30. `doctor.sh` is the check-up; `tools.sh` prints the agent's full toolbox; `housekeeping.sh` runs the cleanup now.
