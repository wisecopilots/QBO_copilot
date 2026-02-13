# Troubleshooting Guide

Common issues and their solutions when running QBO Copilot.

---

## Startup Issues

### "SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set"

**Cause:** The bot cannot find the required Slack tokens in the environment.

**Fix:**
1. Verify `config/.env` exists and contains both tokens:
   ```bash
   cat config/.env | grep SLACK
   ```
2. Make sure the `.env` file is in `config/.env` (not the project root)
3. Verify there are no extra spaces or quotes around values:
   ```bash
   # Correct:
   SLACK_BOT_TOKEN=xoxb-123456

   # Wrong:
   SLACK_BOT_TOKEN = "xoxb-123456"
   ```
4. If running from a different directory, use an absolute path or cd to the project root

### "QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set"

**Cause:** QBO OAuth credentials are not configured.

**Fix:**
1. Check that `QBO_CLIENT_ID` and `QBO_CLIENT_SECRET` are in `config/.env`
2. Get these values from [developer.intuit.com](https://developer.intuit.com) under your app's Keys & credentials tab
3. Make sure you are using the correct environment's keys (sandbox vs production)

### "Module not found" errors

**Cause:** Dependencies not installed or virtual environment not activated.

**Fix:**
```bash
# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

If the virtual environment does not exist:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### "No module named 'slack_bolt'"

**Cause:** Slack SDK not installed.

**Fix:**
```bash
pip install slack-bolt slack-sdk
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

---

## OAuth and Authentication

### OAuth callback errors

**Cause:** Redirect URI mismatch or incorrect credentials.

**Fix:**
1. Verify the redirect URI in your Intuit app settings is exactly:
   ```
   http://localhost:8080/callback
   ```
2. Check that `QBO_CLIENT_ID` and `QBO_CLIENT_SECRET` match what is shown on developer.intuit.com
3. Make sure you are using the correct environment's keys (sandbox keys for sandbox, production keys for production)
4. Re-run the OAuth flow:
   ```bash
   python3 qbo/oauth.py
   ```

### "401 Unauthorized" from QBO API

**Cause:** Access token expired or invalid.

**Fix:**
- The `QBOClient` auto-refreshes tokens on 401 responses. If you still see this error, the refresh token may have also expired.
- Re-run the OAuth flow to get fresh tokens:
  ```bash
  python3 qbo/oauth.py
  ```
- Verify the token file exists:
  ```bash
  ls config/tokens/
  ```

### "Token refresh failed: 400"

**Cause:** Refresh token has expired (after 100 days of inactivity) or is invalid.

**Fix:**
- Re-authorize by running the full OAuth flow:
  ```bash
  python3 qbo/oauth.py
  ```
- Select the same QBO company when prompted

### "Invalid state parameter" during OAuth

**Cause:** Session mismatch between the authorization request and callback.

**Fix:**
- Do not reuse old browser tabs. Start a fresh OAuth flow:
  ```bash
  python3 qbo/oauth.py
  ```
- Use the browser tab that opens automatically (or paste the fresh URL)

---

## Slack Bot Issues

### Bot does not respond to messages

**Possible causes and fixes:**

1. **Socket Mode not enabled:**
   - Go to your app settings at [api.slack.com/apps](https://api.slack.com/apps)
   - Navigate to **Settings > Socket Mode**
   - Ensure it is toggled ON

2. **Bot not invited to the channel:**
   - In Slack, type: `/invite @QBO Copilot`
   - For DMs, open a direct message with the bot

3. **Bot process not running:**
   - Check that `python3 integrations/slack/bot.py` is running
   - Check the terminal for error messages

4. **Event subscriptions not configured:**
   - In app settings, go to **Event Subscriptions**
   - Verify these events are listed: `app_mention`, `message.im`, `message.channels`, `message.groups`, `app_home_opened`

5. **Wrong App-Level Token:**
   - The `SLACK_APP_TOKEN` (xapp-) is different from the Bot Token (xoxb-)
   - Regenerate it from **Basic Information > App-Level Tokens** with `connections:write` scope

### "/qbo command failed" or "dispatch_failed"

**Cause:** The bot process is not connected or the slash command is not registered.

**Fix:**
1. Verify the bot is running and connected (check logs for "A new session has been established")
2. Check that the `/qbo` command is registered in your app's **Slash Commands** settings
3. Reinstall the app to the workspace if the command was added after initial installation

### Bot responds slowly

**Possible causes:**
- Claude API latency (typically 2-10 seconds for a response)
- QBO API latency (1-5 seconds per query)
- Network issues

**Fix:**
- Check Anthropic API status at [status.anthropic.com](https://status.anthropic.com)
- Monitor bot logs for timing information
- Ensure your server has a stable internet connection

---

## Receipt Scanning Issues

### Receipt scanning not working

**Cause:** Missing Anthropic API key or configuration issue.

**Fix:**
1. Verify `ANTHROPIC_API_KEY` is set in `config/.env`:
   ```bash
   grep ANTHROPIC config/.env
   ```
2. Test the API key works:
   ```bash
   python3 -c "import anthropic; c = anthropic.Anthropic(); print('OK')"
   ```

### Scan returns low confidence or incorrect data

**Fix:**
- Use a clear, well-lit photo of the document
- Crop the image to show only the document (remove background)
- Higher resolution images produce better results
- Try a different document type classification if the extraction seems off

### "Parse error" in scan results

**Cause:** Claude's response could not be parsed as JSON.

**Fix:**
- Check the bot logs for the raw response text
- This typically happens with very blurry images, non-document images, or unusual layouts
- Try re-uploading a clearer image

### File upload not triggering scan

**Cause:** The bot may not be detecting the file share event.

**Fix:**
- Upload the file directly to the bot's DM (not a channel)
- Ensure the `files:read` scope is granted to the app
- Check that `message.im` is in the event subscriptions

---

## Google Drive Issues

### "Permission denied" errors

**Cause:** Service account does not have access to the target folder.

**Fix:**
1. Verify the service account email has Editor access to the root folder
2. The email is in the JSON key file as `client_email`
3. Share the root folder with that email from the Google Drive web interface

### "Credentials not found"

**Cause:** Service account JSON file not found.

**Fix:**
1. Check `GOOGLE_SERVICE_ACCOUNT_PATH` in `config/.env`
2. Verify the file exists at that path:
   ```bash
   ls -la config/google-service-account.json
   ```
3. The path can be relative to the project root or absolute

### Files not appearing in Drive

**Fix:**
1. Check bot logs for upload errors
2. Verify `GOOGLE_DRIVE_ROOT_FOLDER_ID` is set correctly
3. Confirm the folder ID matches the folder shared with the service account
4. Make sure the Google Drive API is enabled in your GCP project

---

## Database Issues

### "SQLite database locked"

**Cause:** Multiple processes trying to write to the SQLite database simultaneously.

**Fix:**
1. Ensure only one instance of the bot is running
2. Restart the bot:
   ```bash
   # Find and kill existing processes
   ps aux | grep bot.py
   kill <pid>

   # Restart
   python3 integrations/slack/bot.py
   ```
3. If the issue persists, the database file may be corrupted. The database can be recreated (it auto-creates on startup):
   ```bash
   # Back up existing data
   cp qbo_copilot/data/onboarding.sqlite qbo_copilot/data/onboarding.sqlite.bak

   # Remove and restart (will recreate empty)
   rm qbo_copilot/data/onboarding.sqlite
   python3 integrations/slack/bot.py
   ```

### Migration errors

**Cause:** A SQL migration file has an error.

**Fix:**
- All migrations use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`, so they are safe to re-run
- Check the migration files in `qbo_copilot/data/migrations/` for syntax errors
- The bot applies all `.sql` files in sorted order on startup

---

## QBO API Issues

### Rate limiting

**Cause:** Too many API requests in a short period. QBO has throttling limits.

**Fix:**
- QBO sandbox has more lenient limits than production
- Space out bulk operations
- The bot does not currently implement rate limiting -- if you hit limits consistently, consider adding delays between requests

### "400 Bad Request" when creating entities

**Cause:** Invalid data sent to the QBO API.

**Fix:**
- Check that required fields are provided (e.g., `DisplayName` for customers)
- Customer and vendor `DisplayName` values must be unique in QBO
- Invoice `customer_id` must reference an existing customer
- Date fields must be in `YYYY-MM-DD` format

### "Stale Object" error (SyncToken mismatch)

**Cause:** The entity was modified by someone else between read and update.

**Fix:**
- Fetch the entity again to get the current `SyncToken`
- Retry the update with the new SyncToken
- This is QBO's optimistic locking mechanism

---

## Debugging

### Enable debug logging

Add this to the top of `bot.py` or set the environment variable:

```bash
# Environment variable
export LOG_LEVEL=DEBUG
```

Or in Python:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Check bot logs

The bot logs to stdout. Key things to look for:
- `Agent initialized with N tools` -- Startup successful
- `A new session has been established` -- Slack connection active
- `Token refresh` messages -- OAuth tokens being refreshed
- `Vision response` -- Receipt scanning output
- Exception tracebacks -- Errors with full context

### Test QBO connection directly

```bash
# Test accounts query
python3 qbo/client.py accounts

# Test specific query
python3 qbo/client.py query "SELECT * FROM Account MAXRESULTS 5"

# Test customer list
python3 qbo/client.py customers
```

### Test the agent without Slack

```bash
python3 agent/main.py
```

This starts an interactive CLI where you can type queries and see how the agent processes them.

### Verify environment variables

```bash
# Check what is loaded
python3 -c "
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('config/.env'))
import os
print('QBO_CLIENT_ID:', 'set' if os.getenv('QBO_CLIENT_ID') else 'MISSING')
print('QBO_CLIENT_SECRET:', 'set' if os.getenv('QBO_CLIENT_SECRET') else 'MISSING')
print('ANTHROPIC_API_KEY:', 'set' if os.getenv('ANTHROPIC_API_KEY') else 'MISSING')
print('SLACK_BOT_TOKEN:', 'set' if os.getenv('SLACK_BOT_TOKEN') else 'MISSING')
print('SLACK_APP_TOKEN:', 'set' if os.getenv('SLACK_APP_TOKEN') else 'MISSING')
print('QBO_ENVIRONMENT:', os.getenv('QBO_ENVIRONMENT', 'not set'))
"
```

---

## Getting Help

If you cannot resolve an issue:

1. Check the bot logs for error messages and tracebacks
2. Search existing GitHub issues for similar problems
3. Open a new issue with:
   - The error message (full traceback if available)
   - What you were trying to do
   - Your Python version (`python3 --version`)
   - Your OS (macOS, Linux, Windows)
   - Whether you are using sandbox or production
