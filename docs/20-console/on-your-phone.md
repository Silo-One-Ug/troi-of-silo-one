---
title: On your phone
description: The console as an app on your phone, and the three ways to reach Troi from it, Tailscale first.
order: 9
---

Open the console's address on your phone and it lays itself out as an app:

- a bar at the top: the agent's name and state, the page's title, and the lock (the PIN opens in a
  sheet);
- five tabs at the bottom: **Talk**, **Views**, **Library**, **Approvals** (with its count) and
  **More**;
- **More** holds everything else, one tap away: Modes, Routines, Reports, Eyes, Browser,
  notifications, appearance (auto, light, dark), the lock, and the welcome;
- the five views open full screen from **Views**, with a pill at the bottom to come back. In the
  galaxies: tap a star, drag it onto a folder, press and hold for the menu, pinch to zoom;
- the conversation is its own tab, with a round field and a send button; the floating pane is a
  desktop shape and does not exist here. "Float the conversation" simply opens the Talk tab.

In Safari, **Share › Add to Home Screen** installs it with its own icon and no browser chrome. A
phone held sideways keeps the same layout; an iPad gets the desktop console, with the lock opening
the PIN sheet. Nothing is missing on the phone: every page and every switch of the desktop console
is here.

## Reaching Troi from the phone

**It is off until you turn it on.** The agent answers only on the Mac itself by default. Modes ›
**Your phone** offers two ways beyond that, both protected changes (your PIN), both taking effect at
Troi's next start:

| Option | Who can reach Troi | Use it when |
| --- | --- | --- |
| **This Mac only** | nothing beyond this Mac | the default |
| **Tailscale** | your own devices, from anywhere, over Tailscale; every other network is turned away before a byte is read | you have Tailscale on the Mac and the phone (recommended) |
| **This network** | any phone on this Wi-Fi | a network you trust; anyone on it can talk to Troi and read its record |

### Tailscale

[Tailscale](https://tailscale.com) makes a private network of your own devices, wherever they are,
with nothing opened to the internet. It is the way to reach Troi from the phone.

1. Install Tailscale on the Mac and on the phone, and sign both in to the same account (the same
   tailnet). On the Mac, the app's menu shows the Mac's Tailscale address, such as
   `100.101.102.103`, and its name on the tailnet.
2. Start Troi, so its server sees Tailscale, then in Modes › **Your phone** pick **Tailscale** and
   enter your PIN. The hint under the switch shows the exact address to open.
3. Start Troi again (Ctrl-C in its Terminal window, then the Desktop shortcut).
4. On the phone, with Tailscale on, open `http://<the Mac's Tailscale address>:3100` in Safari and
   add it to the Home Screen.

Use the address, not the `.ts.net` name: browsers insist on https for every `ts.net` name (the
domain is on the HSTS preload list) and the console speaks plain http, so the name ends in "failed
to establish a secure connection". The address stays the same for as long as the Mac is on the
tailnet.

In this mode the agent's server accepts connections from this Mac and from Tailscale addresses
only (`100.64.0.0/10` and Tailscale's IPv6 range); a phone on the same Wi-Fi without Tailscale is
refused. The server also recognises the Mac's tailnet name and addresses as its own, so the console
opened at that name talks to it. The console's own pages (`:3100`) are served on every interface as
before; without the server behind them they show nothing of the record.

### This network

Pick **This network**, enter your PIN, start Troi again, and open `http://<your Mac's name>.local:3100`
on the phone, on the same Wi-Fi (the hint shows the name). Do this only on a network you trust.

### What does not reach the phone yet

The Face and Hands views need their own servers reachable, and those still answer on the Mac only,
so those two views stay blank on the phone. The galaxies, the Vault, the conversation and every page
work.
