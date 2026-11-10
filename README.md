# hacs-integration skill

An [Agent Skill](https://agentskills.io) for creating, building and reviewing
Home Assistant custom integrations distributed through HACS, and for getting
them into the HACS default store.

| File | Purpose |
| --- | --- |
| `skills/hacs-integration/SKILL.md` | Entry point: create / build / review / publish workflows |
| `skills/hacs-integration/references/hacs-requirements.md` | HACS publishing rules, `hacs.json`, `manifest.json`, brands, workflows, check → fix table, hacs/default PR procedure |
| `skills/hacs-integration/references/ha-best-practices.md` | Home Assistant developer guidance and the quality-scale checklist |
| `skills/hacs-integration/references/common-pr-feedback.md` | What closed hacs/default submissions were actually stopped for |
| `skills/hacs-integration/scripts/hacs_preflight.py` | Offline checker for a local integration repository (Python 3.10+, no dependencies) |

### Install

Claude Code, for one project or for yourself:

```bash
cp -r skills/hacs-integration <your-repo>/.claude/skills/
cp -r skills/hacs-integration ~/.claude/skills/
```

Other agents that support the Agent Skills format: copy the
`hacs-integration` directory into that tool's skills directory. On claude.ai,
zip the directory and upload it under Settings → Capabilities → Skills.

Then ask things like "scaffold a HACS integration for my heat pump",
"review this integration before I submit it to HACS", or "why is the HACS
action failing?".

### Run the checker on its own

```bash
python3 skills/hacs-integration/scripts/hacs_preflight.py /path/to/integration-repo
```

Exit code 1 means at least one blocking problem was found.

### Keeping it current

HACS and Home Assistant requirements change. The references were written in
November 2026 from <https://hacs.xyz/docs/publish/start>,
<https://hacs.xyz/docs/publish/include>,
<https://developers.home-assistant.io>,
<https://github.com/ludeeus/integration_blueprint> and closed pull requests in
<https://github.com/hacs/default>.

## Licence

[MIT](LICENSE)
