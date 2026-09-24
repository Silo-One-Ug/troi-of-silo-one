---
status: active
project: meta
type: guide
---
# Server Maintenance

**The job:** A server changed state (a "(server watch: NEW … RESOLVED …)" line) or __OWNER__ asks how the servers are.

## The procedure
1. `__ROOT__/troi-console/servers.py check [name]` — read-only: load, disk, memory, failed services, containers, updates, reboot needed.
2. Tell __OWNER__ in a sentence, worst first.
3. Look deeper read-only (logs, `systemctl status`, `df`, `docker ps`), then propose the fix with its risk.
4. Change nothing on a server without __OWNER__'s go in this conversation. After a fix, check again and say what changed.

## Quality bar
- Evidence from the server, never guesses. One change at a time. Never restart or delete anything on your own.
