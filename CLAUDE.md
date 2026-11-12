# home-assistant-marketplace-skills

An Agent Skill (`skills/marketplace-integration/`) distributed as a Claude
Code plugin. The plugin manifest is `.claude-plugin/plugin.json`.

## Checks

```bash
python -m unittest discover -s tests -v
ruff check .
```

## Versioning

Plugin installs only pick up a change when `version` in
`.claude-plugin/plugin.json` changes. A change merged without a bump never
reaches them.

Bump the version, in the same pull request, for any change to what users
receive: anything under `skills/` or `.claude-plugin/`. Do not bump for
changes to the README, tests, CI or this file alone.

- Patch (`0.2.0` → `0.2.1`): added or corrected guidance, script fixes.
- Minor (`0.2.1` → `0.3.0`): a new mode, skill or pre-flight check, or
  anything that changes how the skill is invoked or named.
- Major: not before the maintainer decides to call it 1.0.

One bump per pull request, however many commits it has. If the branch
already bumped the version, add to that entry instead of bumping again.

With every bump, add a section to the top of `CHANGELOG.md`:
`## [X.Y.Z] - YYYY-MM-DD`, then `Added` / `Changed` / `Fixed` / `Removed`
lists written for a user of the skill, not as a commit log. A test checks
that the newest changelog section matches the manifest version.

## Releasing

A release is how people who watch the repository learn of an update. It is
made after the pull request is merged, from `main`:

1. Confirm CI is green on the merge commit.
2. Create a GitHub release with a new tag `vX.Y.Z` on that commit, titled
   `vX.Y.Z`, with the matching `CHANGELOG.md` section as its notes.

The maintainer publishes releases. Do not create a tag or release unless
asked to in the conversation, never tag a branch other than `main`, and
never move or re-create an existing tag; fix a bad release with a new
patch version.
