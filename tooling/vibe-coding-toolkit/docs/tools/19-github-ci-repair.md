# GitHub CI repair

`gh-fix-ci` is OpenAI's curated GitHub Actions investigation skill. Use it to identify a failing pull-request check, read its logs, explain the cause, and validate a targeted fix. See the [official skill](https://github.com/openai/skills/tree/main/skills/.curated/gh-fix-ci) and [OpenAI skills guidance](https://learn.chatgpt.com/docs/build-skills).

## Requirements and installation

The machine needs the GitHub CLI, repository access, authentication for the intended host/account, and a compatible Python runtime for the bundled inspection script. Reuse the active login; `gh auth status` checks it without printing a token. Never copy authentication into the repository.

Prefer the client's supported curated-skill installer when available. For portable project installation through the [skills CLI procedure](16-vercel-skills.md#local-installation), select the exact source and client:

```bash
npx --yes skills@latest add https://github.com/openai/skills/tree/main/skills/.curated/gh-fix-ci --skill gh-fix-ci --agent codex --yes
```

The upstream workflow targets Codex. Another client must support its instructions and tools before adoption; copying files alone is not compatibility evidence. Keep source/license resources and the project lockfile. Avoid duplicate global and local copies.

## Use and validation

```text
Use gh-fix-ci to investigate the failing checks for this pull request.
Identify the failing GitHub Actions job and relevant log evidence, explain the
root cause, and follow the skill's fix-approval requirements before editing.
Run the relevant local checks and distinguish them from a successful remote run.
```

Start with read-only PR/check/run inspection. External CI systems may expose only a details URL; record that boundary rather than inventing logs. Handle expired login, missing permissions, unavailable logs, and jobs still running explicitly. Sanitize logs before sharing them.

The skill's investigation does not authorize comments, pushes, merges, secret changes, or rerunning privileged workflows. Follow the user's existing authorization and the source workflow's approval requirements. A local passing test does not prove the remote check passed; report the exact commit/run when remote validation is available.

## Maintenance

Use the curated installer's update mechanism or update the selected project skill, according to how it was installed. Review changed instructions and source/lockfile revisions. Verify discovery in a fresh Codex session and a read-only check query against an authorized PR; without one, report installation/discovery only. Record pending account access separately in the machine inventory or project setup report.
