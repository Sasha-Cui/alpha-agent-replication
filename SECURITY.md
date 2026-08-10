# Security Policy

## Supported version

Security and integrity fixes are applied to the current `main` branch. Tagged
releases are immutable; a correction receives a new version and changelog entry.

## Reporting

Do not place credentials, restricted-data locations, or exploitable details in
a public issue. Use GitHub's private vulnerability-reporting interface for this
repository when available; otherwise contact the repository owner privately
through their verified GitHub profile before public disclosure. Include the
affected commit, a minimal reproduction, impact, and suggested remediation.

## Research-data incidents

Accidental inclusion of licensed observations, security identifiers, access
tokens, or non-public source material is a security incident. Stop distribution,
record the affected commit and artifact hashes, rotate exposed credentials, and
coordinate history remediation with the data owner. Never “fix” such an incident
only by deleting the latest file while leaving prior Git objects unaddressed.
