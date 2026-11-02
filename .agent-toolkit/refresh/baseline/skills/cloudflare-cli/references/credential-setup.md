# Cloudflare credential setup

Use this reference only when credentials need initial setup, replacement, or a new profile. Ordinary operations reuse existing credentials through the helper.

## Create the credential

Have the user create the initial token through [Cloudflare's token setup](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/). The user enters it directly into their secret store; do not ask them to paste it into chat. A token-management credential can create later tokens through the [API](https://developers.cloudflare.com/fundamentals/api/how-to/create-via-api/), but do not grant token-management permissions merely to avoid this one-time human step.

Choose permissions for the actual operations and limit accounts, zones, and resources where the selected API supports it. Deployment and data administration can need different grants; do not use a global API key as a shortcut. Verify current [Developer Platform permissions](https://developers.cloudflare.com/workers/authorization/) and endpoint documentation rather than copying a permanent broad scope list. Use distinct profiles for different accounts or privilege levels when useful. Account-owned and user-scoped tokens are not interchangeable for every API.

## macOS Keychain

Use a generic-password item with service `portable-agent-toolkit.cloudflare` and account `default`, or another explicit profile name. With the standard macOS `security` tool, place `-w` last and supply no password argument: it prompts for the secret rather than putting it in shell history or the process command line.

Run this yourself in a local interactive terminal, entering the token only at its password prompt:

```sh
/usr/bin/security add-generic-password -U -s portable-agent-toolkit.cloudflare -a default -w
```

Replace `default` with a chosen profile name for additional credentials. This updates the item if it already exists. Keychain Access is an alternative for entering the same service/account pair. Do not weaken item access to allow all applications. The first helper read may prompt you to authorize `/usr/bin/security`; keep the normal Keychain access control.

The helper retrieves only the selected item and never stores a credential itself. It does not search alternate profiles when a lookup fails. Replacing or deleting that item changes subsequent helper invocations; also revoke an old token at Cloudflare when rotation requires it.

## Other secret managers and CI

Supply `CLOUDFLARE_API_TOKEN` to the process through an established secret manager or CI secret injection. `CLOUDFLARE_ACCOUNT_ID` is optional when the project already declares its account; explicit `--account-id` overrides it. Each invocation resolves its own credential, so noninteractive agent shells do not depend on `.zshrc` exports.

When using an environment-injected token, omit `--profile`; that option explicitly selects macOS Keychain. Worker `.dev.vars` and application `.env` files are not this helper's credential source. It does not load them or install a global CLI, MCP server, shell hook, or user-level agent configuration.

## Validate access

1. Run `doctor` to confirm local availability without disclosing the token.
2. Run the installed Wrangler's `whoami --json` through `run`, or use `api GET /user/tokens/verify` for a user API token.
3. Confirm the identity and intended account, then perform a read appropriate to the work, such as listing the intended account's Workers. A successful identity/token check alone does not establish all required product permissions. Account-owned tokens may require their account-scoped verification endpoint instead of `/user/tokens/verify`.

Do not deploy or provision anything just to test authentication. If there is no credential yet, report setup as pending and provide the exact human step; do not fall back to an interactive OAuth login unasked.
