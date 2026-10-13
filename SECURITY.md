# Security

## Reporting a problem

Please report security problems privately, not in a public issue: on GitHub, open this repository's
**Security** tab and choose **Report a vulnerability**. Say what you found and how to see it happen. You'll get
a reply, and a fix in a release, as soon as possible.

## What Cuánto protects, and how

| What | How |
| --- | --- |
| Your budgets, rates, profiles | Saved only on your computer; atomic writes; unreadable files are set aside, never overwritten; a copy is kept before an import changes a budget |
| Formulas | Read by Cuánto's own small parser (`cuanto/core/formula.py`): numbers, + − × ÷, parentheses and global names only. Nothing is ever evaluated as code |
| Files from other tools (CSV, JSON) | Data only: size-capped, read through the same checks as Cuánto's own files (lengths capped, unknown fields ignored, wrong types dropped) |
| Spreadsheets out | Values only; text that starts like a formula stays text |
| Logos | Read and saved again as a PNG (an SVG is drawn into one), size-capped; the original file is never kept as it came |
| The account sign-in | In the system keychain only (`cuanto/services/secrets.py`); never in a file or a log |
| Links | `cuanto/core/web.py`: https only, public internet addresses only (checked on every redirect, and the connection goes to the checked address), size and unpacking caps |
| Text on screen | Names and imported text are always shown as plain text, never as formatting |
| Updates | Only from this repository's releases; the SHA-256 must match; a signed Mac app must be replaced by one signed by the same developer |
| The build | GitHub Actions pinned to exact commits; the signing certificate only in the signing step; dependencies pinned, with Dependabot proposing updates |
