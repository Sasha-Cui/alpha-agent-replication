# Contributing

Keep changes narrow, reviewable, and explicit about their effect on the evidence.
Start with [the current study](docs/CURRENT_STUDY.md), then the protocol for the
specific code or result you intend to change.

## Development

Use the [development guide](docs/DEVELOPMENT.md) for existing Bouchet environments,
isolated setup elsewhere, and validation scopes. For documentation changes:

```bash
python scripts/check_repository_docs.py
```

Run focused software checks for changed code. Historical submission validation,
source execution, financial recomputation, and model calls are different
operations; none should be launched merely to tidy documentation.

## Research changes

Changes to inputs, clocks, methods, benchmarks, inference, or claims need
source references and a versioned protocol fixed before inspecting new
strategy outcomes. Explain which elements are native, transferred, reconstructed,
or unavailable.

Preserve completed and failed runs. Write a new version rather than editing
frozen outputs, helpers, source bindings, request bodies, or sealed manuscripts
in place. Do not replace a central mechanism with a generic proxy.

## Publication and access

Do not add credentials, licensed security-level inputs, derived holdings,
private response/accounting stores, installed environments, or large archives
to the public source tree. Third-party material retains its original license.

A proposed commit must be reviewed for sensitive content and files over 100 MB.
Commits, pushes, releases, and pull requests require an explicit user request
in this workspace. Repository cleanup does not authorize them.
