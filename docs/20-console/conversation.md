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
- **Clear the chat.** The eraser in the header (in the top bar on a phone) empties the page and
  remembers where it stood, so a reload stays clear; "Show what came before" brings the lines back.
  The record and the agent's memory of the conversation are untouched: for a fresh start of those,
  say or type "clear the session".
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

## The composer

On the desktop the composer is one card. The words go on top; under them the **+** opens a menu
(add files or photos, take a screenshot of the Mac, point at a file with `@`), the clip is a
shortcut to files and photos, and on the right stand the microphone for a voice note and the
arrow that sends. While a reply is under way the arrow becomes **Stop**.

## Files

A file can go with a line, and the agent reads it before it answers:

- **Point at a file on the Mac.** Type `@` and the picker lists your folders (the file roots and the
  vault); keep typing to search by name, ↑ ↓ to move, Enter to pick. The line carries the file's
  path as `@/path/to/file.xlsx`; a folder works too.
- **Attach a file or a photo.** The + menu or the clip opens the file chooser (on a phone, Photos
  and Files); a file dropped on the composer or pasted into it is attached the same way. A photo
  shows as its thumbnail above the words, any other file as a small card with its type and size,
  while it uploads into `data/blobs/uploads/` on the Mac; × leaves one out. It travels as the same
  `@` mention.
- **A screenshot.** "Take a screenshot" in the + menu captures the Mac's screen through the agent's
  own eyes and attaches it like a photo.
- **What the agent does with it.** It reads every mentioned file before answering: text, code,
  pictures and PDFs directly; spreadsheets (xlsx as tables, csv), slides and Word documents through
  `troi-console/read.py`, which prints them as text. Say what you want done with it in the same
  line.

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

## Floating over every app

The floating pane lives inside the console's window. When you want the conversation with you in
every app, the ring lends it a panel of its own: translucent, resizable from its edges, dragged by the
thin strip at its top, above other windows and present on every space, and you can type into it from
wherever you are. Choosing the floating shape in the console, "float the conversation" by voice, or
`console.sh float on` raise it; the column shape, "put the conversation away" or `console.sh float
off` put it away; the ring's menu has "Show / hide the conversation" too. Its place and size are
remembered. It shows the console's `/float` route, the conversation alone.
