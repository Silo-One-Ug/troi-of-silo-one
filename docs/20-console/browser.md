---
title: Browser
description: The agent's browser, mirrored live on the console. Watch it work, or take over.
order: 8
---

The Browser page mirrors the agent's own Chrome live (its own profile and window). Watch it work, or
take over: click, scroll, type, use the address bar, log in to a site for it. **Window** brings the
real browser window forward. When the agent drives your own Chrome through the Playwright extension
there is no port to mirror, so the page has no live view and you watch the real window instead.

When a site needs your account and it is not signed in, the agent opens the page, says "it needs
your login; the Browser page is yours", and waits. Nothing the page shows is taken by the agent as an
instruction to change anything.

"Open the browser on the console" and "show me the browser" bring the page up by voice. The bridge
that mirrors the browser follows whichever tab the agent works in and leaves your tabs and the
console's own tab alone.

Which browser, how it is started and what the agent may do in it: [The browser](../40-abilities/the-browser.md).
