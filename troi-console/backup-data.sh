#!/bin/bash
# The agent's own record, backed up to a private GitHub repo (backup_repo in the settings; created on first run as
# <you>/troi-of-silo-one-backups): each backup is one release with a consistent snapshot of data/troi.db and a
# tarball of the blobs that are new since the last backup (the first one carries them all). Add-only: nothing is
# ever deleted there. Restore: the newest troi.db, and every blobs tarball unpacked in order into data/.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
source "$(cd "$(dirname "$0")" && pwd)/settings.sh"
command -v gh >/dev/null && gh auth status >/dev/null 2>&1 || { echo "data backup: skipped (gh is not signed in: gh auth login)"; exit 0; }
[ -f "$DATA/troi.db" ] || { echo "data backup: nothing to back up yet"; exit 0; }
REPO="$(_get "$CONFIG" backup_repo "")"
if [ -z "$REPO" ]; then REPO="$(gh api user -q .login 2>/dev/null)/troi-of-silo-one-backups"; fi
gh repo view "$REPO" >/dev/null 2>&1 || { gh repo create "$REPO" --private --description "Troi of Silo One: backups of the agent's record" >/dev/null 2>&1 && echo "data backup: created the private repo $REPO" || { echo "data backup: could not create $REPO"; exit 1; }; }
TAG="backup-$(date +%Y-%m-%d-%H%M)"; W="$(mktemp -d)"; MARK="$DATA/.last-backup"
/usr/bin/sqlite3 "$DATA/troi.db" ".backup '$W/troi.db'" && gzip -9 "$W/troi.db" || { echo "data backup: the snapshot failed"; exit 1; }
FILES=("$W/troi.db.gz")
if [ -f "$MARK" ]; then NEW="$(cd "$DATA" && find blobs -type f ! -name '.*' -newer "$MARK" | wc -l | tr -d ' ')"; LIST=$(cd "$DATA" && find blobs -type f ! -name '.*' -newer "$MARK")
else NEW="$(cd "$DATA" && find blobs -type f ! -name '.*' | wc -l | tr -d ' ')"; LIST=$(cd "$DATA" && find blobs -type f ! -name '.*'); fi
if [ "$NEW" -gt 0 ]; then (cd "$DATA" && printf '%s\n' "$LIST" | tar -czf "$W/blobs.tar.gz" -T -) && FILES+=("$W/blobs.tar.gz"); fi
touch "$W/.stamp"
if gh release create "$TAG" -R "$REPO" --title "$TAG" --notes "The record and $NEW new file(s) from the blob store." "${FILES[@]}" >/dev/null 2>&1; then
  mv "$W/.stamp" "$MARK"; echo "data backup: $TAG to $REPO ($NEW new file(s), record $(du -h "$W/troi.db.gz" | cut -f1))"
else echo "data backup: upload failed (offline?); it will carry these files next time"; fi
command rm -rf "$W"
