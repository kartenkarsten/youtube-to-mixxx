# Security policy

## Supported versions

Security fixes are made against the latest code on the default branch.

## Reporting a vulnerability

Please do not report exploitable vulnerabilities in a public issue. Use GitHub's **Report a vulnerability** option in the repository's Security tab (private vulnerability reporting must be enabled by the repository owner). Include the affected version, impact, and steps to reproduce.

The local bridge listens only on loopback and requires a per-installation token. It runs with the permissions of the logged-in user; local applications and browser extensions already running as that user are outside this isolation boundary.
