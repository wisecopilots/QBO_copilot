# QBO OAuth Setup

This guide walks you through connecting QBO Copilot to QuickBooks Online via OAuth 2.0.

## Overview

QBO Copilot uses OAuth 2.0 to authenticate with the Intuit QuickBooks API. The flow works like this:

1. A local server starts on `http://localhost:8080`
2. Your browser opens the Intuit authorization page
3. You sign in and grant access to a QBO company
4. Intuit redirects back to the local server with an authorization code
5. The code is exchanged for access and refresh tokens
6. Tokens are saved locally for ongoing API access

---

## Step 1: Create an Intuit Developer Account

1. Go to [developer.intuit.com](https://developer.intuit.com)
2. Click **Sign Up** (or sign in if you already have an account)
3. Complete the registration process

## Step 2: Create a New App

1. From the Intuit Developer dashboard, click **Create an app**
2. Select **QuickBooks Online and Payments** as the platform
3. Give your app a name (e.g., "QBO Copilot")
4. Click **Create**

## Step 3: Get Your Client ID and Client Secret

1. In your app's dashboard, go to the **Keys & credentials** tab
2. You will see two environments: **Sandbox** and **Production**
3. Start with the **Sandbox** keys (you can switch to production later)
4. Copy the **Client ID** and **Client Secret**

Add them to your `config/.env` file:

```bash
QBO_CLIENT_ID=ABc123...your_client_id
QBO_CLIENT_SECRET=xyz789...your_client_secret
QBO_ENVIRONMENT=sandbox
```

## Step 4: Configure the Redirect URI

1. Still on the **Keys & credentials** tab, scroll to **Redirect URIs**
2. Add the following URI:

```
http://localhost:8080/callback
```

3. Click **Save**

This must match exactly. The local OAuth server in `qbo/oauth.py` listens on this address.

## Step 5: Run the OAuth Flow

With your Client ID and Client Secret in `config/.env`, run:

```bash
python3 qbo/oauth.py
```

For the sandbox environment specifically:

```bash
python3 qbo/oauth.py --sandbox
```

What happens:

1. A local HTTP server starts on port 8080
2. Your default browser opens the Intuit authorization page
3. If the browser does not open, the URL is printed in the terminal -- copy and paste it manually
4. Sign in to your Intuit account
5. Select the QBO company you want to connect
6. Click **Connect**
7. You are redirected back to `localhost:8080/callback`
8. The page shows "Connected to QBO company {realm_id}"
9. Tokens are saved automatically

## Step 6: Verify the Connection

Test that the tokens work by querying your QBO data:

```bash
python3 qbo/client.py accounts
```

You should see a JSON response with your Chart of Accounts. If you see accounts listed, the connection is working.

---

## Token Storage

Tokens are saved in two locations under `config/tokens/`:

| File | Purpose |
|------|---------|
| `config/tokens/default.json` | Default company tokens, used when no realm_id is specified |
| `config/tokens/{realm_id}.json` | Company-specific tokens, used for multi-tenant setups |

Each token file contains:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "AB11...",
  "token_type": "bearer",
  "expires_in": 3600,
  "realmId": "4620816365178805"
}
```

**Important:** These files contain sensitive credentials. They are excluded from version control via `.gitignore`. Do not share them or commit them to a repository.

## Token Refresh

You do not need to manually refresh tokens. The `QBOClient` class handles this automatically:

- When a QBO API request returns a `401 Unauthorized` response, the client uses the `refresh_token` to obtain a new `access_token`
- The new tokens are saved back to the token file
- The original request is retried with the new access token

Refresh tokens are valid for 100 days. If a refresh token expires (e.g., the bot has been offline for 100+ days), you need to re-run the OAuth flow:

```bash
python3 qbo/oauth.py
```

## Sandbox vs Production

| Setting | Sandbox | Production |
|---------|---------|------------|
| API Base URL | `sandbox-quickbooks.api.intuit.com` | `quickbooks.api.intuit.com` |
| Real data | No (test data only) | Yes |
| Rate limits | More lenient | Stricter |
| Requires app review | No | Yes |

Set the environment in `config/.env`:

```bash
QBO_ENVIRONMENT=sandbox    # for development/testing
QBO_ENVIRONMENT=production # for real data
```

To use production:
1. Switch to the **Production** keys on developer.intuit.com
2. Update `QBO_CLIENT_ID` and `QBO_CLIENT_SECRET` in `config/.env`
3. Set `QBO_ENVIRONMENT=production`
4. Re-run the OAuth flow (`python3 qbo/oauth.py`)

Note: Production apps may need to go through Intuit's app review process before they can connect to real QBO companies.

---

## Adding More Companies

To connect additional QBO companies (for multi-tenant use):

1. Run the OAuth flow again: `python3 qbo/oauth.py`
2. Sign in and select the new company
3. New tokens are saved as both `default.json` and `{realm_id}.json`
4. Add the company to `config/clients.yaml` (see [setup-multi-tenant.md](setup-multi-tenant.md))

Each company gets its own token file identified by its realm ID.

---

## Troubleshooting

### "QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set"

The OAuth script cannot find your credentials. Verify:
- The file `config/.env` exists
- It contains both `QBO_CLIENT_ID` and `QBO_CLIENT_SECRET`
- There are no extra spaces or quotes around the values

### "Authorization failed" in the browser

- Double-check your Client ID and Client Secret
- Ensure you are using the correct environment's keys (sandbox vs production)
- Verify the redirect URI is exactly `http://localhost:8080/callback` in your Intuit app settings

### "Invalid state parameter"

This is a security check. It means the callback did not match the expected session. Try running the OAuth flow again from scratch. Do not reuse old browser tabs.

### "Token exchange failed: 400"

- The authorization code may have expired (they are single-use and short-lived)
- Re-run `python3 qbo/oauth.py` to start a fresh flow

### "Token refresh failed: 400"

Your refresh token has expired (after 100 days of inactivity). Re-run the full OAuth flow:

```bash
python3 qbo/oauth.py
```

### Port 8080 already in use

Another process is using port 8080. Either stop that process or wait for it to finish. On macOS/Linux, you can check what is using the port:

```bash
lsof -i :8080
```

### Browser does not open automatically

Copy the URL printed in the terminal and paste it into your browser manually. The URL starts with `https://appcenter.intuit.com/connect/oauth2?...`.
