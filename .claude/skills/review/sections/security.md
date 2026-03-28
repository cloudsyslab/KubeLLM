# Security Review Section

## Focus Areas

Examine the codebase for vulnerabilities that could be exploited by an
attacker. Prioritize issues that are reachable from external input over
theoretical vulnerabilities in internal code.

## What to Look For

### Input Handling (Critical)
- SQL injection: string interpolation in queries instead of parameterized
- XSS: unsanitized user input rendered in HTML/templates
- Command injection: user input passed to shell commands, exec, eval
- Path traversal: user-controlled file paths without sanitization
- Deserialization of untrusted data (pickle, yaml.load, JSON.parse of
  user-controlled schemas)

### Authentication & Authorization (Critical)
- Missing auth checks on endpoints that modify data
- Hardcoded credentials, API keys, or secrets in source code
- Weak password hashing (MD5, SHA1 without salt, custom crypto)
- JWT issues: missing signature verification, algorithm confusion, no expiry
- Session management: predictable tokens, missing invalidation

### Data Exposure (Warning)
- Sensitive data in logs (passwords, tokens, PII)
- Verbose error messages exposing internals to users
- API responses including more data than the client needs
- Missing rate limiting on sensitive endpoints
- CORS misconfiguration allowing unauthorized origins

### Dependency Security (Warning)
- Known vulnerable dependencies (check lock files for outdated packages)
- Unpinned dependency versions that could be supply-chain attacked
- Dependencies with excessive permissions or suspicious provenance

### Cryptography (Warning)
- Use of deprecated algorithms (DES, RC4, MD5 for security purposes)
- Hardcoded IVs or predictable random number generation
- Missing TLS/HTTPS enforcement
- Insufficient key lengths

## What to Skip

- Theoretical vulnerabilities in dead code or unreachable paths
- Style-level issues (variable naming in security-related code)
- Performance of security operations (unless it enables DoS)
- Dependencies that are dev-only and never reach production

## Severity Guide

| Severity | Criteria |
|----------|----------|
| Critical | Exploitable from external input, could lead to data breach or RCE |
| Warning | Security weakness that requires specific conditions to exploit |
| Suggestion | Defense-in-depth improvement, not immediately exploitable |
