---
title: Conversation
description: Everything the agent hears and says, live. Typing, the two shapes, the ignored lines, and the cards it draws.
order: 2
---

Everything the agent hears and says, live, in the same session as your voice, Telegram and calls.
The window takes the console's full width; the words keep a reading column in the middle.

- **Your lines** are bubbles on the right, with your initials beside them and the time in the
  corner. **The agent's replies** sit straight on the page, and under each one a copy button takes
  the reply as written, with the time beside it.
- A reply grows word by word, then settles into the finished text.
- **What it is doing.** While the agent works, one line under your message shows the tool in its
  hands and what it is on: the command, the file, the search, the page. The line shimmers, and each
  new step takes the last one's place, so the conversation never fills with them. When the reply
  comes, the line settles into a count of the steps by kind (commands, files, searches); click it to
  see them all.
- Faint **"ignored"** lines show what the filters dropped and why: a rejected voice shows its
  similarity score, and a line with no wake word says so.
- **Type** and press Enter. A typed turn is answered here and out loud on the Mac, like a spoken
  one.
- **Replies keep their shape.** A reply of several sentences is one bubble, and it renders
  Markdown: headings, lists, tables, code, links. The agent shapes an answer that has structure
  (items, steps, a comparison, numbers, a snippet) and keeps prose plain; the voice reads the words,
  never the marks.
- Charts, tables, pictures and players the agent draws appear right in the conversation
  ([Drawing in the conversation](../40-abilities/drawing.md)). Pictures from research and headlines
  from the news land here as cards too.
- A reload keeps the conversation: the console loads the last lines from the record when it opens.
- Scroll up to read and the page stays where you are; a **Latest** pill (with a count of what has
  arrived meanwhile) takes you back to the end.

## Files

A file can go with a line, and the agent reads it before it answers:

- **Point at a file on the Mac.** Type `@` and the picker lists your folders (the file roots and the
  vault); keep typing to search by name, ↑ ↓ to move, Enter to pick. The line carries the file's
  path as `@/path/to/file.xlsx`; a folder works too. - **Attach a file.** The clip opens the file
  chooser (on a phone, Photos and Files); a file dropped on the composer or pasted into it is
  attached the same way. It is uploaded into `data/blobs/uploads/` on the Mac, shown as a chip until
  you send (× leaves it out), and travels as the same `@` mention. - **What the agent does with
  it.** It reads every mentioned file before answering: text, code, pictures and PDFs directly;
  spreadsheets (xlsx as tables, csv), slides and Word documents through `troi-console/read.py`,
  which prints them as text. Say what you want done with it in the same line.

Pictures you attach also appear in the Library under Uploads.

## On a phone

The composer is a messenger's: the field grows with the lines (Return makes a new line; the plane
sends), and while the field is empty a **microphone** stands where the plane will be. Tap it, speak,
tap the plane: the note goes to the agent's own ears on the Mac, and the words it heard appear as
your line and are answered like any other. × throws a recording away. The microphone needs an https
address on a phone ([On your phone](on-your-phone.md)); over plain http, Telegram voice notes are the
way to talk.

## Two shapes

It comes in two shapes, switched with the icon on its header, and your choice is remembered.

- **The column** is the Conversation page itself.
- **The floating pane** follows you onto every other page: drag it by the grip above its header,
  resize it from its corner, and double-click the grip to put it back. "Float the conversation",
  "hide the conversation" and "tidy up" do the same by voice.

On the phone the conversation is its own tab, **Talk**, with a round field and a send button; the
floating pane is a desktop shape and does not exist there.

## Stopping and interrupting

**Stop** (the square button) or **Esc** stops a reply; so does saying "stop". While the agent is
talking the send button becomes Stop.
