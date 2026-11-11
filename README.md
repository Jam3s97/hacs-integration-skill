# hacs-integration skill

An [Agent Skill](https://agentskills.io) that helps you create, build and
review Home Assistant custom integrations distributed through
[HACS](https://hacs.xyz), and get them accepted into the HACS default store.

It knows the HACS publishing rules, Home Assistant's developer best practice,
and what maintainers actually ask for: it was built from the review comments
on 80 real submissions to [hacs/default](https://github.com/hacs/default).

Integrations only. It does not cover dashboards, cards or themes.

## Install

You need [Claude Code](https://claude.com/claude-code) (the terminal app or
the VS Code extension). Run these on your own computer, in a terminal. In
VS Code, open one with **Terminal → New Terminal**.

### For all your projects (recommended)

macOS, Linux or WSL:

```bash
git clone https://github.com/Jam3s97/hacs-integration-skill
mkdir -p ~/.claude/skills
cp -r hacs-integration-skill/skills/hacs-integration ~/.claude/skills/
```

Windows (PowerShell):

```powershell
git clone https://github.com/Jam3s97/hacs-integration-skill
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse hacs-integration-skill\skills\hacs-integration "$HOME\.claude\skills\"
```

### For one integration's repository only

Copy the folder into that repository instead, and commit it:

```bash
mkdir -p /path/to/your-integration/.claude/skills
cp -r hacs-integration-skill/skills/hacs-integration /path/to/your-integration/.claude/skills/
```

Use this route for Claude Code on the web: cloud sessions only see what is in
the repository.

### Check it worked

Start a **new** Claude Code chat (a chat that was already open will not see
the skill) and type `/hacs-integration`. It should appear in the command
list. If it does not, check that this file exists:
`~/.claude/skills/hacs-integration/SKILL.md`.

### Updating

```bash
cd hacs-integration-skill && git pull
cp -r skills/hacs-integration ~/.claude/skills/
```

### Other tools

- **claude.ai app:** zip the `skills/hacs-integration` folder and upload it
  under Settings → Capabilities → Skills.
- **Other agents that support Agent Skills:** copy `skills/hacs-integration`
  into that tool's skills directory.

## Use

Open your integration's repository in Claude Code, then either type the
command or just ask in plain language; the skill loads itself when the
request is about a HACS integration.

| You want to | Type | Or just ask |
| --- | --- | --- |
| Start a new integration | `/hacs-integration create` | "Scaffold a HACS integration for my heat pump" |
| Add or fix code | `/hacs-integration build` | "Add a reauth flow to this integration" |
| Check it before submitting | `/hacs-integration review` | "Review this integration before I submit it to HACS" |
| Fix a failing check | `/hacs-integration review` | "Why is the HACS action failing?" |
| Submit to the HACS default store | `/hacs-integration publish` | "Help me submit this to hacs/default" |
| Answer a maintainer's review | `/hacs-integration respond` | "Here's the review on my HACS PR, help me fix it" (paste it) |

### What a review gives you

`/hacs-integration review` runs the pre-flight checker, reads your code, and
reports findings in three groups, each with a file, line and fix:

- **Blocking**: a HACS or hassfest check will fail, or the PR would be closed
- **Should fix**: Home Assistant best practice and bugs users would hit
- **Nice to have**

It cannot see your GitHub settings from a local folder, so it will also ask
you to confirm a few things by hand: repository description, topics, issues
enabled, and that a release was published after the checks passed.

### Run the checker on its own

The pre-flight script works without Claude. It needs Python 3.10 or later and
nothing else:

```bash
python3 ~/.claude/skills/hacs-integration/scripts/hacs_preflight.py /path/to/your-integration
```

It prints `ERROR`, `WARN` and `INFO` lines. Exit code 1 means at least one
blocking problem was found, so it can be used in CI.

## What's inside

| File | Purpose |
| --- | --- |
| `skills/hacs-integration/SKILL.md` | Entry point: the create, build, review, publish and respond workflows |
| `skills/hacs-integration/references/hacs-requirements.md` | HACS publishing rules, `hacs.json`, `manifest.json`, brand images, workflows, a check → fix table, and the hacs/default PR procedure |
| `skills/hacs-integration/references/ha-best-practices.md` | Home Assistant developer guidance and a quality-scale checklist |
| `skills/hacs-integration/references/common-pr-feedback.md` | What closed hacs/default submissions were stopped for |
| `skills/hacs-integration/references/review-rounds.md` | What reviewers asked for on submissions that were merged, and how to respond to a review |
| `skills/hacs-integration/scripts/hacs_preflight.py` | The offline checker |

## Keeping it current

HACS and Home Assistant requirements change several times a year. The
references were written in November 2026 from:

- <https://hacs.xyz/docs/publish/start> and
  <https://hacs.xyz/docs/publish/include>
- <https://developers.home-assistant.io>
- <https://github.com/ludeeus/integration_blueprint>
- pull requests in <https://github.com/hacs/default>

If the skill and the live documentation disagree, the documentation wins.
Issues and pull requests are welcome.

## Licence

[MIT](LICENSE)
