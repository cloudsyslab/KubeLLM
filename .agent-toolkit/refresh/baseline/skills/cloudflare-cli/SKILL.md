---
name: cloudflare-cli
description: Use Wrangler and the Cloudflare API for Cloudflare administration, deployment, diagnostics, and credential setup without routine dashboard navigation.
---

# Cloudflare CLI

Use the project's existing Wrangler version and Cloudflare's REST API for authorized Cloudflare work. A dashboard session is unnecessary for supported operations once API credentials are available. The browser workflow applies when rendered interaction is actually needed.

## Choose the operation and target

- Read the project's Wrangler configuration, package scripts, and deployment instructions. Run commands from the directory that owns that configuration; prefer its pinned binary or `npx --no-install wrangler` over a global install or an unpinned download.
- Confirm the selected account, environment, Worker, zone, and resource before mutations. Use explicit account IDs or repository configuration rather than guessing from a logged-in dashboard or choosing the first account returned.
- Prefer Wrangler for Worker deployments, versions, secrets, tail logs, D1, KV, R2, and other operations exposed by the installed version. Check that version's `--help`; capabilities evolve.
- Use the bundled API helper when the installed Wrangler lacks the operation. Resolve the endpoint and required permissions from current official documentation through [Discovery](../discovery/SKILL.md). Avoid ad hoc commands that place an Authorization header or token in process arguments.
- Credential availability is not authorization to deploy, change production, delete resources, or broaden token permissions. Preserve the task's existing authorization boundaries.

## Resolve credentials once

The bundled [helper](scripts/cloudflare.py) uses an inherited `CLOUDFLARE_API_TOKEN`, then the `default` macOS Keychain profile. An explicit `--profile NAME` selects that Keychain entry exclusively: it ignores inherited token and account credentials. Profiles let projects share machine-level storage without reusing the wrong ambient credential.

Keychain items use service `portable-agent-toolkit.cloudflare` and account equal to the profile name. On other systems, supply the environment through the user's existing secret manager. Credentials never belong in the repository, skill, Wrangler config, or an agent transcript.

Run the local presence check first:

```sh
python3 .agents/skills/cloudflare-cli/scripts/cloudflare.py doctor
```

This checks availability only. It does not prove the token is valid, has sufficient permissions, or belongs to the intended account. Then check authenticated identity with the project's installed Wrangler:

```sh
python3 .agents/skills/cloudflare-cli/scripts/cloudflare.py run -- npx --no-install wrangler whoami --json
```

These examples assume the Wrangler project is at the repository root. For a nested project, enter its directory and adjust the helper path. The helper preserves the caller's working directory, streams output with exact-token redaction, and returns the command's exit status. It passes the token only through the child environment and removes legacy global-key credentials that could conflict with it. Avoid commands that intentionally print credentials, including `wrangler auth token`, `env`, `printenv`, and shell tracing; output redaction is not a sandbox for arbitrary commands.

If credentials are missing, expired, locked, or insufficient, identify that specific problem. Read [credential setup](references/credential-setup.md) when setup or rotation is needed. Do not automatically run `wrangler login`, open a dashboard, search browser profiles for credentials, or repeatedly retry the same authentication failure. A first-time Keychain access prompt may require the user to authorize the item locally.

## Direct API requests

The helper attaches the bearer token internally and allows only relative paths on `https://api.cloudflare.com/client/v4`. It refuses redirects, preventing credentials from being forwarded to a different destination. It makes one request without automatic retries or pagination; inspect the response metadata and request additional pages explicitly when needed.

```sh
python3 .agents/skills/cloudflare-cli/scripts/cloudflare.py api GET /user/tokens/verify
python3 .agents/skills/cloudflare-cli/scripts/cloudflare.py --profile client-one --account-id ACCOUNT_ID api GET '/accounts/{account_id}/workers/scripts'
```

An explicit Keychain profile clears inherited account selection; supply `--account-id` for API account placeholders or rely on the project's Wrangler configuration for Wrangler commands. API mutations accept `--data-file request.json` (or `--data-file -` for JSON on stdin). Keep sensitive request bodies outside version control and avoid printing secret-bearing responses.

The API helper returns nonzero on HTTP errors, network failures, and JSON responses with `success: false`. Diagnose permission failures against the selected endpoint and resource. Some APIs have distinct token requirements, such as Workers Builds requiring user-scoped tokens; do not respond by silently switching identity or granting broad account access.

Use the dashboard for a documented UI-only operation or a necessary human bootstrap/consent step. Explain the concrete gap first. Keep any rendered work in the selected browser workflow.

## Authoritative references

- [Wrangler authentication environment variables](https://developers.cloudflare.com/workers/wrangler/system-environment-variables/)
- [Wrangler commands](https://developers.cloudflare.com/workers/wrangler/commands/)
- [Cloudflare API](https://developers.cloudflare.com/api/)
- [Workers Builds API token requirements](https://developers.cloudflare.com/workers/ci-cd/builds/api-reference/)
