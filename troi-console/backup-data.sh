#!/bin/bash
# The agent's own record, backed up to a private GitHub repo (backup_repo in the settings; by default
# <backup_org>/troi-of-silo-one-backups, created on the first run as github_account): each backup is one release with a consistent snapshot of data/troi.db and a
# tarball of the blobs that are new since the last backup (the first one carries them all). Add-only: nothing is
# ever deleted there. Restore: the newest troi.db, and every blobs tarball unpacked in order into data/.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
source "$(cd "$(dirname "$0")" && pwd)/settings.sh"
command -v gh >/dev/null && use_github_account || { echo "data backup: skipped ($GITHUB_ACCOUNT is not signed in to gh: gh auth login)"; exit 0; }
[ -f "$DATA/troi.db" ] || { echo "data backup: nothing to back up yet"; exit 0; }
REPO="$(_get "$CONFIG" backup_repo "")"; [ -n "$REPO" ] || REPO="$BACKUP_ORG/troi-of-silo-one-backups"
README="$(printf '# Troi of Silo One: backups\n\nOne release per night: the agent record (troi.db.gz) and the files that are new since the night before (blobs.tar.gz).\nRestore: the newest troi.db, then every blobs tarball unpacked in order into data/.\n')"
gh repo view "$REPO" >/dev/null 2>&1 || { gh repo create "$REPO" --private --description "Troi of Silo One: backups of the agent's record" >/dev/null 2>&1 && echo "data backup: created the private repo $REPO" || { echo "data backup: could not create $REPO as $GITHUB_ACCOUNT"; exit 1; }; }
if [ "$(gh repo view "$REPO" --json isEmpty -q .isEmpty 2>/dev/null)" = "true" ]; then     # a release needs a commit to tag
  gh api -X PUT "repos/$REPO/contents/README.md" -f message="backups: what is here" -f content="$(printf '%s' "$README" | base64)" >/dev/null 2>&1 || { echo "data backup: could not start $REPO"; exit 1; }
fi
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
