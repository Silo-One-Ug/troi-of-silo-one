---
status: active
project: meta
type: guide
---
# Code Review

**The job:** Review a pull request or local changes (`pr.py review …`, a headless session of yours with read-only tools) and report in plain language.

## The procedure
1. Read the whole diff, then the files it touches, enough to understand the change in context.
2. Look for, in order: correctness bugs (with the input that breaks it), security problems, data loss, broken contracts between parts, missing tests for new behaviour, needless complexity.
3. Report: a one-line verdict (ship / fix first / rethink), then each finding with the file and line, why it matters, and the smallest fix. Nitpicks last, marked as such, and only a few.

## Quality bar
- Every finding is concrete: a line, an input, an outcome. No generic advice. Never post to the PR unless __OWNER__ said to.
