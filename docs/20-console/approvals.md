---
title: Approvals
description: The page where requests wait for you, how approving works, and what expires.
order: 6
---

Cards for trash, force-quit, risky-click and protected-setting requests, and a record of earlier
decisions. The bar shows a count of what is waiting; so does the globe's badge, and a notification
and a sound cue announce a new one.

- **Approving needs the console unlocked**: your PIN at the lock, or **Check it's me** on the Eyes
  page. Rejecting never does.
- **On Telegram**, "approve" or "reject" decides the newest request that is waiting.
- **Requests wait across a restart**, except risky clicks, which expire because the screen has moved
  on.
- **What you approve for removal goes to the macOS Trash**, never further. An approved force-quit
  quits the app; an approved risky click replays as a click at the control's position; an approved
  protected setting applies.

The agent never approves its own request, and cannot: the approval and unlock endpoints are among
the safeguards the guard keeps from it. What needs approval, and why, is on
[Approvals](../50-safety/approvals.md) in the Safety section.
