# Governance

## Roles

| Role | Who | Can |
|---|---|---|
| Maintainers | Listed in `.github/CODEOWNERS` | Merge pull requests, cut releases, publish weights, moderate |
| Contributors | Anyone with a merged pull request | Review pull requests, triage issues |
| Users | Everyone | Open issues, discussions and pull requests |

## How decisions are made

- Day-to-day changes: one maintainer approval and green CI.
- Changes to the wire format, a default model, the eval suites or the security model: an issue first, then two
  maintainer approvals. These affect every client.
- A new model becomes the default only with a benchmark report produced by the scripts in this repository, on
  held-out suites it never trained on (see the rules in [CONTRIBUTING.md](CONTRIBUTING.md)).

## Numbers policy

Every published number comes from a real run that anyone can repeat. Vendor numbers are labelled "vendor-reported",
with a link. Eval cases are never deleted or relabelled to improve a score. A wrong label is fixed in the open,
with the reason.

## Releases

Semantic Versioning for the package; model ids (`decider-X.Y.Z`) never change meaning once published, so pinned
clients keep their behaviour. Each release follows [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) and is recorded in
[CHANGELOG.md](CHANGELOG.md).

## Code of conduct

Everyone follows the [Code of Conduct](CODE_OF_CONDUCT.md).
