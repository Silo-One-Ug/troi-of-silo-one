---
title: Meetings
description: Recording a meeting, the speaker-labelled transcript, and the meeting note in the vault.
order: 8
---

"Record this meeting" / "start recording": a recording begins, from **Meeting In** when it exists
(the Mac's microphone plus BlackHole, with the Mac's sound routed through **Meeting Out** until
stop), or from the microphone alone without BlackHole. "Stop recording" ends it. Started from a
calendar heads-up, the recording takes the event's title.

"Transcribe it": a speaker-labelled transcript with ElevenLabs Scribe (it needs the ElevenLabs key
in the Keychain, and says how many credits it used). From that transcript the agent writes the
meeting note into the vault, following the Meeting Prep & Notes job, and puts your action items on
Active Priorities. A file you hand it (a recording, a video) transcribes the same way.

Recordings and transcripts stay in `data/blobs/meetings/`. From a terminal, `meeting.py devices`,
`start <name> [--device NAME]`, `stop`, `status`, `transcribe <file> [--lang xx] [--speakers N]` and
`list` are the same tools.
