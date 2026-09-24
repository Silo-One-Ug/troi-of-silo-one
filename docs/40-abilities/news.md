---
title: News
description: Headlines per outlet, Uganda first, read out or on the board; a subject across every outlet; an article read out; an outlet's videos and social pages.
order: 6
---

"What's in the news", "what's trending in Uganda", "what does NBS say about the budget": the agent
reads the outlets listed in `troi-console/news.json`. Out of the box:

- **Uganda:** NBS Television, Nile Post (Next Media), NTV Uganda, UBC, Galaxy FM, Simba FM, The
  Independent, The Observer, PML Daily, and Google News for Uganda.
- **World:** BBC World, BBC Africa, Al Jazeera, The Guardian and The Washington Post.

It can:

- give the latest per outlet, with how old each story is (it speaks the top three or four, with
  their outlets, and offers to read one out);
- put a front page of cards on the board;
- search every outlet for a subject;
- read an article out;
- list an outlet's latest YouTube videos;
- open its X or Facebook page in its browser when you ask what they are posting.

Outlets without a working website (UBC, Simba FM) are covered through Google News and YouTube. A
single outlet's claim is labelled as that outlet's; a headline is never presented as verified fact.

Edit `news.json` to add or drop outlets; feeds, Google News queries and handles are all it needs.
