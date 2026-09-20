# CLAUDE.md

Conventions, hard rules and working procedures for this repository are in
[`AGENTS.md`](./AGENTS.md). Read it before making changes.

Current state — what has been run against a real account and what has not — is
in [`STATUS.md`](./STATUS.md).

Two things that are easy to get wrong and expensive to get wrong:

- **Nothing that bills runs without asking.** Deploying an endpoint, launching a
  Pod and `terraform apply` all cost money on a live account.
- **Written is not deployed.** Check `STATUS.md` before assuming a lab has been
  exercised.

Before committing documentation changes:

```bash
python3 scripts/check-docs.py -v
```
