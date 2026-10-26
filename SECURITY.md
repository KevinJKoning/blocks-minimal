# Security

Security fixes target the latest code on `main`. Older revisions have no separate
security support.

Please report suspected vulnerabilities privately through
[GitHub's vulnerability reporting form](https://github.com/KevinJKoning/blocks-minimal/security/advisories/new).
Include the affected revision, steps to reproduce, and the expected impact. Avoid
public issues or pull requests that disclose an unpatched vulnerability, and use
synthetic data instead of real credentials or private datasets in reproductions.

Apps execute trusted Python code. Only open apps and run node code from sources
you trust. The browser isolation and offline build protections described in the
README reduce exposure to dependencies; they do not make untrusted app code safe.
