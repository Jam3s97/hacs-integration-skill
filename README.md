# Home Assistant Marketplace skills

[![CI](https://github.com/Jam3s97/home-assistant-marketplace-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Jam3s97/home-assistant-marketplace-skills/actions/workflows/ci.yml)

> If you find this useful, please give it a ⭐ on GitHub

[Agent Skills](https://agentskills.io) for people who publish to the
**Home Assistant Marketplace**, which is the new name for HACS now that it is
built into Home Assistant (from 2026.11 on).

There is one skill so far, **`marketplace-integration`**. It helps you create,
build and review a custom integration.
It can also help refine your integration if you wish to get it added into the
Marketplace catalog, the list you may know as the HACS default store.

It knows the Marketplace and HACS publishing rules, Home Assistant's developer
best practice, and what maintainers actually ask for: it was built from the
review comments on 80 real submissions to
[hacs/default](https://github.com/hacs/default).

Integrations only for now. Skills for dashboards, cards and themes may follow.

### HACS or Marketplace?

Both. The Marketplace is HACS under a new name, and most of the pieces kept
theirs:

- the catalog is still the [hacs/default](https://github.com/hacs/default)
  repository
- your repository still needs a `hacs.json`
- the check is still the HACS action
- if you are on Home Assistant 2026.10 or older, you still use HACS, and
  everything here applies

> **Unofficial.** This is a community project. It is not affiliated with or
> endorsed by Home Assistant, HACS or the Open Home Foundation.

## Using AI responsibly

The aim is better and safer integrations, and less work for the volunteers
who review them, not faster submissions. Home Assistant and HACS fall under
the Open Home Foundation's
[AI policy](https://contributors.home-assistant.io/start/ai-policy/): AI is
welcome as a tool, but you are responsible for what you submit and must
understand it. So the skill is built to:

- explain each problem and fix, so you can explain your own code
- leave the hacs/default pull request, its description and any replies to
  maintainers to you; it will not open the PR, post comments or write your
  replies
- check your work against the rules before a maintainer has to

Please read and test what it produces before you release it.

## Install

Which way to install depends on where you use Claude. The `/plugin` command
only exists in the terminal version of Claude Code; elsewhere it replies
"Plugins aren't available in this environment". The Claude desktop app and
claude.ai have their own plugin screen in Settings instead.

| Where you use Claude | How to install |
| --- | --- |
| Claude Code in VS Code | [Copy the folder](#by-copying-the-folder) |
| Claude Code in a terminal | [Copy the folder](#by-copying-the-folder), or [the plugin command](#as-a-plugin-terminal-only) |
| Claude Code on the web | [Add it to your repository](#for-one-integrations-repository-only) |
| Claude desktop or claude.ai app | [Add the repository in Settings](#as-a-plugin-claude-desktop-and-claudeai) |

The skill is not listed in the plugin store inside the Claude apps until you
add this repository to it; out of the box that store only shows Anthropic's
own directory.

### By copying the folder

Works for the VS Code extension and the terminal. Run these on your own
computer, in a terminal. In VS Code, open one with
**Terminal → New Terminal**. This installs it for all your projects, and the
command is `/marketplace-integration`.

macOS, Linux or WSL:

```bash
git clone https://github.com/Jam3s97/home-assistant-marketplace-skills
mkdir -p ~/.claude/skills
cp -r home-assistant-marketplace-skills/skills/marketplace-integration ~/.claude/skills/
```

Windows (PowerShell):

```powershell
git clone https://github.com/Jam3s97/home-assistant-marketplace-skills
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse home-assistant-marketplace-skills\skills\marketplace-integration "$HOME\.claude\skills\"
```

### For one integration's repository only

Copy the folder into that repository instead, and commit it:

```bash
mkdir -p /path/to/your-integration/.claude/skills
cp -r home-assistant-marketplace-skills/skills/marketplace-integration /path/to/your-integration/.claude/skills/
```

This is the only route that works for Claude Code on the web: cloud sessions
see what is in the repository and nothing from your own computer.

### As a plugin (terminal only)

In Claude Code running in a terminal, type:

```
/plugin install marketplace-skills --marketplace Jam3s97/home-assistant-marketplace-skills
```

On Claude Code older than 2.1.275, use two steps instead:

```
/plugin marketplace add Jam3s97/home-assistant-marketplace-skills
/plugin install marketplace-skills@home-assistant-marketplace-skills
```

Installed this way, the command is `/marketplace-skills:marketplace-integration`
(plugin name, then skill name).

To get new versions automatically, run `/plugin`, open **Marketplaces**,
select `home-assistant-marketplace-skills` and choose **Enable auto-update**.
Claude Code then checks for a new version when it starts. This is off by
default for marketplaces that are not Anthropic's own. To update by hand
instead, run `/plugin marketplace update home-assistant-marketplace-skills`
followed by
`/plugin update marketplace-skills@home-assistant-marketplace-skills`.

### As a plugin (Claude desktop and claude.ai)

1. Open **Settings → Customize → Plugins**.
2. Click **Add**, and in the **Add marketplace** window choose
   **Add from a repository**.
3. Enter `Jam3s97/home-assistant-marketplace-skills`, or the full address
   `https://github.com/Jam3s97/home-assistant-marketplace-skills`.
4. Add the `marketplace-skills` plugin, which now appears in the list.

The pre-flight script needs code execution to be enabled. If your plan or
organization does not show the Plugins tab, upload the skill as a zip instead;
see [Other tools](#other-tools).

### Check it worked

Start a **new** Claude Code chat (a chat that was already open will not see
the skill) and type `/marketplace-integration`. It should appear in the command
list. If it does not: for a plugin install, run `/plugin` and look under
Installed; for a copied folder, check that this file exists:
`~/.claude/skills/marketplace-integration/SKILL.md`.

### Updating a copied folder

```bash
cd home-assistant-marketplace-skills && git pull
rm -rf ~/.claude/skills/marketplace-integration
cp -r skills/marketplace-integration ~/.claude/skills/
```

Deleting the old copy first matters: a plain copy leaves behind files that a
new version removed.

### Other tools

- **Claude desktop or claude.ai app, without the Plugins tab:** zip the
  `skills/marketplace-integration` folder and upload it under
  Settings → Customize → Skills. The pre-flight script needs code execution
  to be enabled there.
- **Other agents that support Agent Skills:** copy `skills/marketplace-integration`
  into that tool's skills directory.

## Use

Open your integration's folder in Claude Code (for a brand new integration,
see [Starting a new integration](#starting-a-new-integration)), then either
type the command or just ask in plain language; the skill loads itself when the
request is about a custom integration for the Marketplace or HACS.

The commands below are for a copied-folder install. If you installed with
the plugin command, type `/marketplace-skills:marketplace-integration` in place of
`/marketplace-integration`.

| You want to | Type | Or just ask |
| --- | --- | --- |
| Start a new integration | `/marketplace-integration create` | "Scaffold a custom integration for my heat pump" |
| Add or fix code | `/marketplace-integration build` | "Add a reauth flow to this integration" |
| Check it before submitting | `/marketplace-integration review` | "Review this integration before I submit it to the Marketplace" |
| Fix a failing check | `/marketplace-integration review` | "Why is the HACS action failing?" |
| Get ready to submit to the Marketplace catalog | `/marketplace-integration publish` | "Is this ready to submit to hacs/default?" |
| Work through a maintainer's review | `/marketplace-integration respond` | "Here's the review on my HACS PR, help me understand and fix it" (paste it) |

### Starting a new integration

You do not need a repository first.
Install the skill for all your projects
(the per-repository install cannot work here, since there is no repository
yet), then pick whichever starting point suits you:

- **An empty folder.** Make a folder, open it in Claude Code (or VS Code),
  and run `/marketplace-integration create`. The skill downloads the
  [integration blueprint](https://github.com/ludeeus/integration_blueprint)
  into it, renames everything for your integration and sets up git. You
  create the GitHub repository afterwards and push to it.
- **A repository made from this awesome [integration blueprint](https://github.com/ludeeus/integration_blueprint).** On the blueprint's GitHub page
  click **Use this template**, clone your new repository, open it, and run
  `/marketplace-integration create`. The skill sees the template is already there
  and goes straight to renaming and filling it in.

Either way it will ask for a few things first: the integration's name and
domain, what device or service it talks to, whether that is local or cloud,
and your GitHub username. It also checks whether Home Assistant or the
Marketplace already has an integration for the same thing, because duplicates are not
accepted into the catalog.

### What a review gives you

`/marketplace-integration review` runs the pre-flight checker, reads your code, and
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
python3 ~/.claude/skills/marketplace-integration/scripts/preflight.py /path/to/your-integration
```

If you installed the plugin, there is no copy at that path; run it from a clone
of this repository instead
(`python3 skills/marketplace-integration/scripts/preflight.py /path/to/your-integration`).

It prints `ERROR`, `WARN` and `INFO` lines. Exit code 1 means at least one
blocking problem was found, so it can be used in CI.

## What's inside

| File | Purpose |
| --- | --- |
| `skills/marketplace-integration/SKILL.md` | Entry point: the create, build, review, publish and respond workflows |
| `skills/marketplace-integration/references/marketplace-requirements.md` | Marketplace and HACS publishing rules, `hacs.json`, `manifest.json`, brand images, workflows, a check → fix table, and the hacs/default PR procedure |
| `skills/marketplace-integration/references/ha-best-practices.md` | Home Assistant developer guidance and a quality-scale checklist |
| `skills/marketplace-integration/references/common-pr-feedback.md` | What closed hacs/default submissions were stopped for |
| `skills/marketplace-integration/references/review-rounds.md` | What reviewers asked for on submissions that were merged, and how to respond to a review |
| `skills/marketplace-integration/scripts/preflight.py` | The offline checker |
| `.claude-plugin/` | Plugin and marketplace manifests for the one-line install |
| `tests/` | Tests for the checker and the skill's structure, run by CI |
| `CHANGELOG.md` | What changed in each version |

## Keeping it current

Marketplace and Home Assistant requirements change several times a year. The
references were written in November 2026 from:

- the Marketplace publishing documentation,
  <https://contributors.home-assistant.io/marketplace/>
- the older HACS pages, <https://hacs.xyz/docs/publish/start> and
  <https://hacs.xyz/docs/publish/include>
- <https://contributors.home-assistant.io>
- <https://github.com/ludeeus/integration_blueprint>
- pull requests in <https://github.com/hacs/default>

If the skill and the live documentation disagree, the documentation wins.

Each version is listed in [CHANGELOG.md](CHANGELOG.md) and published as a
[release](https://github.com/Jam3s97/home-assistant-marketplace-skills/releases).
To be emailed about new versions, click **Watch** on the repository, then
**Custom** and tick **Releases**. A plugin install can update itself (see
[As a plugin](#as-a-plugin-terminal-only)); a copied folder or an uploaded
zip has to be replaced by hand.
Issues and pull requests are welcome.


## Licence

[MIT](LICENSE)
