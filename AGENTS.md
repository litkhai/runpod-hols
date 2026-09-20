# AGENTS.md

Conventions and working rules for this repository. English only — like the nav
and footer, this is tooling rather than lab content.

Read [`README.md`](./README.md) for what the repository *is* and
[`STATUS.md`](./STATUS.md) for what has actually been run.

---

## Hard rules

**Never spend money without asking.** Creating a Pod, deploying an endpoint,
`terraform apply`, or anything that starts a GPU worker bills a real account.
Ask first, every time. Read-only queries — `runpod.get_endpoints()`,
`Endpoint.health()`, `terraform plan`, REST `GET` — are fine unprompted.

**Never commit secrets.** `.env` holds a live API key, is mode 600, and is
gitignored. `scripts/check-docs.py` fails if it is ever tracked.

**Never state a version, API shape, or limit from memory.** Read it from the
installed source, the live API, or the published spec, and say in the document
how it was confirmed. This has caught real errors — see *Things that went
wrong* below.

## The principle everything else follows from

Every claim in these docs was produced by running something. Where that was not
possible, the page says so explicitly rather than presenting the claim as
tested. A reader must always be able to tell which is which.

When you add an unverified claim, label it in place — a callout on the site, a
blockquote in the repo — and add a row to that page's *What is verified here*
table if it has one.

## Writing

**Bilingual, English first.** Every README and site page carries a full
`## English` section and a full `## 한국어` section, mirroring each other. The
Korean is a parallel text, not a translation artifact: same headings, same
tables, same number of them.

**Interface stays English.** Nav labels, footer, `AGENTS.md`, `STATUS.md`. The
language toggle governs content, not chrome.

**State the subject, not the arrangement.** Do not write "This section covers
X", "Two kinds of material, kept apart because…", or "The table below shows".
Say the thing.

**Do not put counts in headings.** A heading like "three places a model can
live" breaks the moment a fourth row is added to the table under it — which is
exactly what happened.

## Layout

```
setup/ serverless/ pod/ cluster/ terraform/   labs, one directory per product
sdk/                                          SDK reference (worker + client)
gpu-topology/                                 GPU concepts reference
docs/                                         Jekyll site, deployed to Pages
scripts/                                      repo tooling
```

Top level is flat: the repository name already says these are labs.

Each lab directory is self-contained — its `Dockerfile` uses bare `COPY` paths
so the folder builds on its own. The cost is that Runpod's console needs its
**Build context** field set to the lab directory; that field is undocumented and
the build fails with `"/handler.py": not found` without it.

Repo documents and site pages are separate files. `sdk/worker.md` is the full
reference; `docs/sdk-worker.md` is the trimmed site version. **When you change a
fact, change both.** A verification pass caught `VolumeCache` living only in the
repo copy while the site page linked to it.

## Verification

```bash
python3 scripts/check-docs.py -v
```

Checks bilingual heading parity, code fences, table columns, `.lang` blocks,
nav-to-permalink consistency, internal links, and tracked secrets. Every check
in it exists because something broke; each one has been mutation-tested to
confirm it actually fires.

**There is no local Jekyll.** The site builds in GitHub Actions
(`actions/jekyll-build-pages`). To verify rendering you push and then fetch the
deployed page. Waiting for the build:

```bash
SHA=$(git rev-parse HEAD)
gh run list --workflow=pages.yml --limit 10 \
  --json headSha,status,conclusion --jq ".[] | select(.headSha==\"$SHA\")"
```

Filter by `headSha`. Listing the newest run right after a push returns the
*previous* commit's run often enough to mislead you.

If a deploy jams, `gh run rerun` is rejected while the run is live. Use
`gh run cancel <id>` then `gh workflow run pages.yml --ref main`.

**Liquid pipes are not broken tables.** `{{ '/x/' | relative_url }}` contributes
a `|` to the Markdown source that never reaches the rendered table. Strip Liquid
before counting columns — `check-docs.py` does.

## Running the labs

Each lab has its own virtualenv at `<lab>/.venv`. Use its interpreter directly:

```bash
serverless/01-hello-worker/.venv/bin/python handler.py
```

Docker builds need `--platform linux/amd64` on Apple Silicon. Runpod hosts are
x86 and an arm64 image fails at run time, not build time.

Endpoint builds from GitHub are **console-only**. The published OpenAPI spec has
23 paths and none of them create a build; `POST /endpoints` takes a
`templateId`. Do not look for an API that does this — verify against
`https://rest.runpod.io/v1/openapi.json` if in doubt.

## Things that went wrong

Kept because each one is a mistake worth not repeating.

| What happened | The lesson |
|---|---|
| Documented log truncation as 10 MB by copying the SDK's own comment. The constant is `MAX_MESSAGE_LENGTH = 4096` | Vendor comments are not evidence. Read the constant |
| Added a fourth row to a table under a heading that said "three places" | Do not put counts in headings |
| Bumped an SDK pin and left "read at 1.11.0" statements across six files | Version claims are facts with a location; grep for all of them |
| Inserted a section at an anchor a previous trim had removed; the edit silently no-op'd | Assert the anchor exists before replacing |
| Claimed GitHub's code index had not picked up the repo; the control query also returned zero | If a negative result has no positive control, it is not a result |
| Watched the wrong workflow run after pushing | Filter runs by `headSha` |
| Flip-flopped on `COPY` paths instead of researching the Build context field | Find the documentation before changing code. When it does not exist, say so |

## Current state

[`STATUS.md`](./STATUS.md). Keep it current when you finish something — it is
the only place that records what has been run against a real account, and a new
agent will otherwise assume written means deployed.
