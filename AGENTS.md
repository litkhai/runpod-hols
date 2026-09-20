# AGENTS.md

Conventions are in [`README.md`](./README.md) → *How This Repository Works*.
What has been run and what has not: [`STATUS.md`](./STATUS.md).

## Never

- **Spend without asking.** Deploying an endpoint, launching a Pod,
  `terraform apply`. Read-only queries need no permission.
- **Commit secrets.** `.env` holds a live key, mode 600, gitignored.
- **State a version, API shape or limit from memory.** Read the installed
  source, the live API or the published spec, and record in the page how it was
  confirmed.
- **Put a count in a heading.** "three places a model can live" broke when a
  fourth row was added under it.
- **Write about the document.** Not "this section covers X" — say the thing.

## Before committing

```bash
python3 scripts/check-docs.py -v
```

Bilingual heading parity, code fences, table columns, `.lang` blocks,
nav-to-permalink consistency, internal links, tracked secrets.

## Not guessable

- **No local Jekyll.** Rendering is verified by pushing and fetching the
  deployed page.
- **Select workflow runs by `headSha`.** Listing the newest run right after a
  push returns the previous commit's often enough to mislead.
- **Stuck deploy:** `gh run cancel <id>`, then
  `gh workflow run pages.yml --ref main`. `gh run rerun` is rejected while live.
- **A Liquid `|` is not a table column.** `{{ '/x/' | relative_url }}` never
  reaches the rendered table. Strip Liquid before counting.
- **Labs run from their own venv:** `<lab>/.venv/bin/python`.
- **GitHub builds are console-only.** The published OpenAPI spec has 23 paths
  and none create a build; `POST /endpoints` takes a `templateId`.
- **Repo doc and site page are separate files** — `sdk/worker.md` and
  `docs/sdk-worker.md`. Change both. A verification pass caught `VolumeCache`
  living only in the repo copy while the site page linked to it.

## Mistakes already made

| What happened | Lesson |
|---|---|
| Documented log truncation as 10 MB, copying the SDK's own comment. The constant is `MAX_MESSAGE_LENGTH = 4096` | Vendor comments are not evidence |
| Bumped an SDK pin, left "read at 1.11.0" across six files | Version claims have locations; grep for all of them |
| Inserted a section at an anchor a previous trim had removed — the edit silently no-op'd | Assert the anchor exists before replacing |
| Claimed GitHub's index lacked the repo; the control query also returned zero | A negative with no positive control is not a result |
| Shipped a docs checker that passed on first run | Passing proves nothing. Inject the fault and watch it fire |
| Flip-flopped on `COPY` paths instead of researching the Build context field | Find the documentation first. When it does not exist, say so |
