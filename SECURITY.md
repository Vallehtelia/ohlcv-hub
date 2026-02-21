# Security Policy

## Reporting a Vulnerability

If you believe you have found a security vulnerability in this project, please report it responsibly:

- **Do not** open a public GitHub issue for security-sensitive findings.
- Contact the maintainers (e.g. via repository contact or private disclosure) with a clear description of the issue and steps to reproduce.
- Allow a reasonable time for a fix before any public disclosure.

## API Secrets and Credentials

- **Never** share API keys, secrets, or tokens in GitHub issues, pull requests, or logs.
- Configuration uses environment variables (`ALPACA_API_KEY`, `ALPACA_API_SECRET`). Keep these out of version control and do not log them.
