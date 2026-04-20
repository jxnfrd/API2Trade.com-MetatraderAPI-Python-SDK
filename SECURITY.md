# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Active  |

## Reporting a Vulnerability

**Please do not report security vulnerabilities via public GitHub Issues.**

If you discover a security issue in the API2Trade Python SDK (e.g. credential
exposure, unsafe defaults, dependency vulnerability), contact us privately:

📧 **security@api2trade.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We aim to acknowledge reports within **48 hours** and release a patch within
**7 days** for confirmed critical issues.

## Credential Safety

The SDK never logs, stores, or transmits your broker password or API key to
any third party. All credentials are only forwarded to the
`api.metatraderapi.dev` endpoint over TLS 1.2+.

**Never commit a real `.env` file to version control.**
Use `.env.example` as the template and add `.env` to your `.gitignore`.
