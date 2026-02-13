# Slack App Setup

This guide walks you through creating and configuring the Slack app for QBO Copilot. The app uses Socket Mode, which means it connects outbound from your server to Slack -- no public URL or webhook endpoint is needed.

## Step 1: Create the Slack App from Manifest

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Select **From an app manifest**
4. Choose your workspace
5. Select **JSON** as the format
6. Paste the contents of `config/slack-app-manifest.json`
7. Click **Next**, review the summary, then click **Create**

The manifest pre-configures everything the bot needs:

| Feature | What It Does |
|---------|-------------|
| **Bot User** | Creates "QBO Copilot" bot identity (always online) |
| **Slash Command `/qbo`** | Registers the `/qbo` command for quick operations |
| **Event Subscriptions** | Listens for DMs, @mentions, channel messages, Home tab opens |
| **Interactivity** | Enables buttons, modals, dropdowns in Block Kit messages |
| **Socket Mode** | Connects without a public URL |
| **Message Shortcuts** | "Convert to Case" and "Request Documents" right-click actions |

## Step 2: Get Your Bot Token

1. In your app settings, go to **OAuth & Permissions** in the left sidebar
2. Click **Install to Workspace** (if not already installed)
3. Authorize the app
4. Copy the **Bot User OAuth Token** -- it starts with `xoxb-`

Add it to `config/.env`:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
```

### Bot Token Scopes

The manifest requests these scopes (you do not need to add them manually):

- `app_mentions:read` -- Detect when someone @mentions the bot
- `channels:history`, `channels:read` -- Read channel messages
- `chat:write` -- Send messages
- `commands` -- Handle slash commands
- `files:read`, `files:write` -- Access uploaded files (for receipt scanning)
- `groups:history`, `groups:read` -- Read private channel messages
- `im:history`, `im:read`, `im:write` -- Handle direct messages
- `mpim:history` -- Read group DMs
- `pins:write` -- Pin messages
- `reactions:read`, `reactions:write` -- Read and add reactions
- `users:read` -- Look up user information

## Step 3: Generate an App-Level Token

1. Go to **Basic Information** in the left sidebar
2. Scroll down to **App-Level Tokens**
3. Click **Generate Token and Scopes**
4. Name the token (e.g., "socket-mode")
5. Add the scope: **`connections:write`**
6. Click **Generate**
7. Copy the token -- it starts with `xapp-`

Add it to `config/.env`:

```bash
SLACK_APP_TOKEN=xapp-your-app-token-here
```

## Step 4: Get the Signing Secret

1. Still on **Basic Information**, scroll to **App Credentials**
2. Copy the **Signing Secret**

Add it to `config/.env`:

```bash
SLACK_SIGNING_SECRET=your_signing_secret_here
```

## Step 5: Enable Socket Mode

1. Go to **Settings > Socket Mode** in the left sidebar
2. Toggle **Enable Socket Mode** to ON

Socket Mode is already specified in the manifest, but verify it is enabled. This is what allows the bot to run behind a firewall without needing a public URL.

## Step 6: Verify Event Subscriptions

Go to **Event Subscriptions** and confirm these bot events are listed:

- `app_mention` -- When someone @mentions the bot
- `app_home_opened` -- When someone opens the bot's Home tab
- `message.im` -- Direct messages to the bot
- `message.channels` -- Messages in public channels
- `message.groups` -- Messages in private channels

These should already be configured from the manifest.

## Step 7: Install the App to Your Workspace

If you have not already done so:

1. Go to **OAuth & Permissions**
2. Click **Install to Workspace**
3. Review the permissions and click **Allow**

---

## Testing the Connection

### Start the bot:

```bash
python3 integrations/slack/bot.py
```

You should see:

```
INFO:__main__:Agent initialized with 25 tools
INFO:slack_bolt.App:A new session has been established
```

### Invite the bot to a channel:

In Slack, type in any channel:

```
/invite @QBO Copilot
```

### Send a test message:

DM the bot or @mention it in a channel:

```
@QBO Copilot show me all accounts
```

The bot should respond with a formatted list of accounts from your connected QBO company.

### Test the slash command:

```
/qbo help
```

This should display the help menu with available subcommands.

---

## Summary of Required Environment Variables

After completing this guide, your `config/.env` should have these three Slack entries:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your_signing_secret
```

---

## Updating the App Later

If you need to change the app configuration (add scopes, modify commands, etc.):

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Select your QBO Copilot app
3. Make changes in the relevant section
4. If you changed OAuth scopes, you will need to reinstall the app to the workspace

You can also update the manifest directly:
1. Go to **App Manifest** in the sidebar
2. Edit the JSON
3. Click **Save Changes**

---

## Troubleshooting

### "SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set"

The bot cannot find the required tokens. Check that:
- `config/.env` exists and contains both `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`
- You are running the bot from the project root directory
- The virtual environment is activated

### Bot does not respond to messages

- Verify Socket Mode is enabled in app settings
- Check that the bot is invited to the channel (`/invite @QBO Copilot`)
- For DMs, make sure the `im:history` and `im:read` scopes are granted
- Check the bot process logs for errors

### "not_authed" or "invalid_auth" errors

- The Bot Token may be incorrect or expired
- Try regenerating the Bot Token from OAuth & Permissions and updating `config/.env`

### Slash command not working

- Verify the `/qbo` command is registered in **Slash Commands** settings
- The manifest should have configured this automatically
- Make sure the bot process is running -- slash commands require an active connection

### "missing_scope" errors

- The app needs additional OAuth scopes
- Go to **OAuth & Permissions**, add the missing scope, then reinstall the app
