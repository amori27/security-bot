# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Below is the support status:

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Active |
| < 1.0   | ❌ No     |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability, **do not** open a public issue.

**Report privately via email:** amir.asaad@gmail.com

Please include:
- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Suggested fix (if any)

You should receive a response within 48 hours. If not, follow up.

## Disclosure Policy

- We will acknowledge receipt within 48 hours
- We will verify and assess impact within 5 business days
- We will release a fix based on severity
- We will notify you when the fix is released
- We will credit you in the release notes (optional)

## Recommendations

- Keep dependencies updated
- Use environment variables for secrets (see `.env.example`)
- Never commit API keys, tokens, or passwords
- Run security audits regularly: `pip-audit`
- Enable GitHub Dependabot for automated dependency scanning
