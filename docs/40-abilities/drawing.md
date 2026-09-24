---
title: Drawing in the conversation
description: Charts, tables, stats, galleries, tabs, maps and players drawn inside the conversation from data, live, and kept in the record.
order: 12
---

Charts, tables, stats, galleries, tabs, maps and players are drawn inside the conversation from
data. The agent runs `show.py` with a component tree (or `show.py chart …` / `show.py table …`), and
the card lands in the conversation, live, and stays in the record. No HTML files, no screenshots of
them, no chart described in words.

```bash
troi-console/show.py chart bar "Rain" month "mm" '[{"month":"Jul","mm":30}]'
troi-console/show.py table "Outlets" "Outlet,Headline" '[["NBS","..."]]'
troi-console/show.py '<json tree>' --title "..."
```

`show.py vocabulary` lists the components: stack, grid, card, stat, progress, kv, list, table,
chart, tabs, image, gallery, embed, map, callout. Pictures from research and headlines from the news
land in the conversation as cards of their own.
