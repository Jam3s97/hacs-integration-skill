# Research log

Where the skill's knowledge came from and where each source was last read, so
the next refresh can start from there instead of repeating work. This file is
for maintainers; it is not part of the skill and is not shipped to users.

## hacs/default pull request reviews

The two reference files `common-pr-feedback.md` and `review-rounds.md` were
compiled from maintainer and bot comments on pull requests in
<https://github.com/hacs/default>.

### Cutoff

**Nothing closed or merged after 2026-11-09 has been read.** At the time, pull
request numbers ran up to roughly #13780. Start the next review from
`closed:>2026-11-09`.

### What was read

| Batch | Read on | Count | Selection | Span covered |
| --- | --- | --- | --- | --- |
| Closed, not merged: most discussed | 2026-11-10 | 20 | `is:closed is:unmerged integration in:title`, sorted by comment count, mostly `comments:>=3 closed:>2025-09-01` | closed 2025-09 to 2026-11-06 |
| Closed, not merged: recent and short | 2026-11-10 | 28 | `is:closed is:unmerged integration in:title comments:1..3 closed:>2026-08-15`, sorted by last update | closed 2026-10-18 to 2026-11-09 |
| Merged after review | 2026-11-11 | 32 | `is:merged integration in:title merged:>2026-07-01 comments:>=4`, sorted by comment count | merged 2026-07-02 to 2026-11-09 |

80 pull requests in total. Individual numbers are deliberately not recorded
here or in the reference files, so that no submitter is singled out.

### Size of the population at the time

Searches on 2026-11-10 for pull requests with "integration" in the title:

- 3,285 closed without merging and 5,346 merged, all time
- 933 closed without merging and 2,796 merged since 2026-06-01
- about 670 open

So the sample is under 1% of the total and is biased towards discussed pull
requests. The counts quoted in the reference files ("7 of 32") describe the
sample, not the population.

### Not covered

- Pull requests closed with no comments at all
- Dashboard plugins, themes and templates (492 plugin submissions were closed
  unmerged in 2026 to that date, against 637 merged)
- Removal and rename pull requests
- Anything before 2025, apart from a few entries in the first batch

### How it was done

1. List candidates with GitHub search, for example:

   ```bash
   gh api -X GET search/issues \
     -f q='repo:hacs/default is:pr is:closed is:unmerged integration in:title closed:>2026-11-09' \
     -f sort=updated -f order=desc -f per_page=60 \
     --jq '.items[] | [.number, .comments, .closed_at[0:10], .title] | @tsv'
   ```

   Swap in `is:merged … merged:>2026-11-09 comments:>=4` and
   `-f sort=comments` for the merged set.
2. Read each pull request page and extract only what maintainers
   (`frenck`, `ludeeus`) and `hacs-bot` wrote: what was wrong and what fix was
   asked for. Search results do not include comment text, so every page has
   to be opened.
3. Tally recurring findings, then fold new ones into the two reference files.
   Keep quotes short and leave out pull request numbers, repository names and
   submitter names.

Things to watch for next time:

- Long pull request pages were cut off at about 40,000 characters when
  fetched, so the last review rounds of the longest threads came from a
  summary rather than the text. Treat those with less confidence, or fetch
  the comments through the API instead.
- Roughly 25 pages per batch is a practical size.
- When a batch mostly repeats earlier findings, stop; the second closed batch
  added only two new categories.

### After a refresh

- Update the cutoff and the table above.
- Update the "Compiled in …" line and the sample sizes at the top of each
  reference file.
- Bump the plugin version and add a `CHANGELOG.md` entry, as `CLAUDE.md`
  describes.

## Documentation sources

| Source | Last read | Notes |
| --- | --- | --- |
| Marketplace publishing docs, <https://contributors.home-assistant.io/marketplace/> | 2026-11-12 | Read from the source repository `home-assistant/contributors.home-assistant.io`: the custom integrations guide, "Get into the catalog", releases, and the `hacs.json`, repository structure and validation references. The dashboard, theme, template and blueprint guides were not read |
| HACS publishing docs, <https://hacs.xyz/docs/publish/> | 2026-11-10 | Read from `hacs/documentation` (last commit then: 2026-10-17): start, include, integration, action, remove |
| HACS validators | 2026-11-10 | `custom_components/hacs/validate/` in `hacs/integration`, for check names and error messages |
| hacs/default workflow and scripts | 2026-11-10 | `.github/workflows/checks.yml` and `scripts/check/` |
| Home Assistant developer docs | 2026-11-10 | From `home-assistant/developers.home-assistant` at the time; that content has since moved to `contributors.home-assistant.io` |
| Open Home Foundation AI policy | 2026-11-12 | <https://contributors.home-assistant.io/start/ai-policy/> |
| Integration blueprint | 2026-11-10 | <https://github.com/ludeeus/integration_blueprint> |

Later changes that drew on other sources are recorded in `CHANGELOG.md`.
