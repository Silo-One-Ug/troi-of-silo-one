---
title: Pictures
description: Research with credited pictures on the board, making pictures from words, and showing a picture or a 3D model.
order: 5
---

## Research with pictures

When the agent researches or explains something that has a look to it (a place, a building, a
product, a species, a design, a person's work, a chart on a page), it puts pictures up while it
talks: free, credited pictures from Wikimedia Commons, Wikipedia and Openverse, the pictures a web
page leads with, or a screenshot of the page.

- **On the board**, they land as a numbered grid under one caption card. Each new topic sweeps the
  last unless the agent is asked to add. It prefers three to six pictures that each say something
  different.
- **Steering**: "focus on the second one" spotlights a picture, and "show them all" brings the rest
  back; "clear the board" clears it.
- **Kept**: they also land in the Library under Research, and in `data/blobs/research/<topic>/` with
  a credits file.
- **To your phone**: "send me those".

## Making pictures

"Draw me a…", "make a picture of…", "imagine…": the agent makes a picture from words, or restyles
one you point it at, saves it in the Library, and can put it on the hands board. It needs an image
key in the Keychain; the welcome's Extras step keeps it, or:

```bash
troi-console/keychain.py set openai     # OpenAI
troi-console/keychain.py set gemini     # Google Gemini
```

`troi-console/imagine.py check` says which backend is on. Pictures and their prompts land in
`data/blobs/imagined/`.

## Showing a picture

"Show me the photo of…", "put that image up", "show me the screenshot": the agent copies the file
into the board's airlock and puts it up in the middle of the board. Pictures it took, Telegram photos,
screenshots, vault attachments and 3D models all work; it asks which one if the request could mean
several. See [The hands board](../30-views/hands-board.md).
