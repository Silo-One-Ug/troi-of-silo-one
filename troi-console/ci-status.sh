#!/bin/bash
# One-screen CI status from GitHub for every org and user the CI watch follows (github_orgs in console.json, set under Routines › CI watch):
# newest main run per repo, open PRs, latest release.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
source "$(cd "$(dirname "$0")" && pwd)/settings.sh"; [ -n "$GH_ORGS" ] || { echo "no GitHub org or user to watch yet: add one under Routines › CI watch"; exit 0; }
for ORG in $GH_ORGS; do
for r in $(gh repo list $ORG --json name -q '.[].name'); do
  echo "== $ORG/$r"
  gh run list -R $ORG/$r -b main -L 2 --json name,status,conclusion,createdAt,displayTitle -q '.[] | "  run: \(.name) \(.status) \(.conclusion // "") \(.createdAt[0:16]) — \(.displayTitle)"'
  gh pr list -R $ORG/$r --json number,title,author,isDraft,updatedAt -q '.[] | "  PR #\(.number) \(if .isDraft then "(draft) " else "" end)\(.title) — \(.author.login), \(.updatedAt[0:10])"'
  gh release list -R $ORG/$r -L 1 --json tagName,publishedAt -q '.[] | "  release: \(.tagName) \(.publishedAt[0:10])"' 2>/dev/null
done
done
