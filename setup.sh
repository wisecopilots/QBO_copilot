#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# QBO Copilot - Interactive Bootstrap Script
# https://github.com/wisecopilots/QBO_copilot
# =============================================================================

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOTAL_STEPS=8
ENV_FILE="$SCRIPT_DIR/config/.env"
ENV_EXAMPLE="$SCRIPT_DIR/config/.env.example"
CLIENTS_YAML="$SCRIPT_DIR/config/clients.yaml"
TOKENS_DIR="$SCRIPT_DIR/config/tokens"
VENV_DIR="$SCRIPT_DIR/venv"

# ---------------------------------------------------------------------------
# Color codes
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

print_step() {
    local step=$1
    local title=$2
    echo ""
    echo -e "${CYAN}${BOLD}[$step/$TOTAL_STEPS] $title${NC}"
    echo -e "${CYAN}$(printf '%.0s-' {1..60})${NC}"
}

info() {
    echo -e "${BLUE}[info]${NC} $1"
}

success() {
    echo -e "${GREEN}[ok]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[warn]${NC} $1"
}

error() {
    echo -e "${RED}[error]${NC} $1"
}

prompt_value() {
    local prompt_text=$1
    local var_name=$2
    local default_value=${3:-}
    local is_secret=${4:-false}

    if [[ -n "$default_value" ]]; then
        echo -ne "${YELLOW}$prompt_text [${default_value}]: ${NC}"
    else
        echo -ne "${YELLOW}$prompt_text: ${NC}"
    fi

    if [[ "$is_secret" == "true" ]]; then
        read -rs input_value
        echo ""
    else
        read -r input_value
    fi

    if [[ -z "$input_value" && -n "$default_value" ]]; then
        input_value="$default_value"
    fi

    eval "$var_name=\"$input_value\""
}

confirm() {
    local prompt_text=$1
    local default=${2:-y}
    local options="Y/n"
    [[ "$default" == "n" ]] && options="y/N"

    echo -ne "${YELLOW}$prompt_text [$options]: ${NC}"
    read -r response
    response=${response:-$default}

    [[ "$response" =~ ^[Yy] ]]
}

set_env_value() {
    local key=$1
    local value=$2
    local file=$3

    # Escape special characters in value for sed (using | as delimiter)
    local escaped_value
    escaped_value=$(printf '%s\n' "$value" | sed 's/[&|\\]/\\&/g')

    if grep -q "^${key}=" "$file" 2>/dev/null; then
        sed -i '' "s|^${key}=.*|${key}=${escaped_value}|" "$file"
    elif grep -q "^# *${key}=" "$file" 2>/dev/null; then
        sed -i '' "s|^# *${key}=.*|${key}=${escaped_value}|" "$file"
    else
        echo "${key}=${value}" >> "$file"
    fi
}

# ---------------------------------------------------------------------------
# --help flag
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "QBO Copilot Setup Script v${VERSION}"
    echo ""
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "This interactive script walks you through the full QBO Copilot setup:"
    echo ""
    echo "  1. Checks system requirements (macOS, Python 3.11+, pip3)"
    echo "  2. Creates a Python virtual environment and installs dependencies"
    echo "  3. Configures environment variables (QBO, Slack, Anthropic, etc.)"
    echo "  4. Runs the QuickBooks Online OAuth authorization flow"
    echo "  5. Creates the multi-tenant client configuration"
    echo "  6. Validates all connections (QBO API, Slack, Anthropic)"
    echo "  7. Optionally launches the Slack bot"
    echo ""
    echo "The script is idempotent -- it detects existing configuration and"
    echo "offers to keep or replace it. Safe to re-run at any time."
    echo ""
    echo "Prerequisites:"
    echo "  - macOS (tested on Ventura+)"
    echo "  - Python 3.11 or later"
    echo "  - A QuickBooks Online developer account"
    echo "  - A Slack workspace with admin access"
    echo "  - An Anthropic API key"
    echo ""
    echo "For detailed docs, see: https://github.com/wisecopilots/QBO_copilot#readme"
    exit 0
fi

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
clear 2>/dev/null || true
echo -e "${CYAN}${BOLD}"
cat << 'BANNER'

     ___  ____   ___     ____            _ _       _
    / _ \| __ ) / _ \   / ___|___  _ __ (_) | ___ | |_
   | | | |  _ \| | | | | |   / _ \| '_ \| | |/ _ \| __|
   | |_| | |_) | |_| | | |__| (_) | |_) | | | (_) | |_
    \__\_\____/ \___/   \____\___/| .__/|_|_|\___/ \__|
                                  |_|

BANNER
echo -e "${NC}"
echo -e "  ${DIM}AI-powered QuickBooks Online assistant for CPAs${NC}"
echo -e "  ${DIM}Version ${VERSION}${NC}"
echo ""
echo -e "${DIM}  This script will walk you through the complete setup process.${NC}"
echo -e "${DIM}  Each step explains what it does and why it is needed.${NC}"
echo -e "${DIM}  Press Ctrl+C at any time to abort.${NC}"
echo ""
echo -e "${DIM}$(printf '%.0s=' {1..60})${NC}"

# ===========================================================================
# Step 1: System checks
# ===========================================================================
print_step 1 "System Requirements"
info "Checking that your system has the tools QBO Copilot needs."

# --- macOS ---
if [[ "$(uname -s)" != "Darwin" ]]; then
    error "This setup script is designed for macOS."
    error "On Linux, install Python 3.11+ and run: pip install -r requirements.txt"
    exit 1
fi

macos_version=$(sw_vers -productVersion 2>/dev/null || echo "unknown")
success "macOS detected (version $macos_version)"

# --- Python 3.11+ ---
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Please install Python 3.11 or later."
    info "Install via Homebrew:  brew install python@3.13"
    info "Or download from:      https://www.python.org/downloads/"
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}')
python_major=$(echo "$python_version" | cut -d. -f1)
python_minor=$(echo "$python_version" | cut -d. -f2)

if [[ "$python_major" -lt 3 ]] || [[ "$python_major" -eq 3 && "$python_minor" -lt 11 ]]; then
    error "Python 3.11+ required, but found Python $python_version"
    info "Install via Homebrew:  brew install python@3.13"
    info "Or download from:      https://www.python.org/downloads/"
    exit 1
fi
success "Python $python_version found"

# --- pip3 ---
if ! command -v pip3 &>/dev/null; then
    error "pip3 not found. It usually ships with Python 3."
    info "Try: python3 -m ensurepip --upgrade"
    exit 1
fi
success "pip3 available"

# --- git (nice to have) ---
if command -v git &>/dev/null; then
    success "git available ($(git --version | awk '{print $3}'))"
else
    warn "git not found. Not required, but recommended for updates."
fi

# ===========================================================================
# Step 2: Virtual environment and dependencies
# ===========================================================================
print_step 2 "Python Virtual Environment"
info "A virtual environment keeps QBO Copilot's dependencies isolated"
info "from your system Python packages."

if [[ -d "$VENV_DIR" ]]; then
    success "Virtual environment already exists at ./venv"
    if confirm "Recreate it from scratch?"; then
        info "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        info "Keeping existing virtual environment."
    fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    success "Virtual environment created at ./venv"
fi

# Activate
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
success "Virtual environment activated"

info "Installing dependencies from requirements.txt..."
pip install --upgrade pip --quiet 2>&1 | tail -1 || true
pip install -r "$SCRIPT_DIR/requirements.txt" --quiet 2>&1 | tail -1 || {
    error "Failed to install dependencies."
    info "Check the output above for errors, then re-run this script."
    exit 1
}
success "All dependencies installed"

# ===========================================================================
# Step 3: Configure .env
# ===========================================================================
print_step 3 "Environment Configuration"
info "QBO Copilot reads credentials and settings from config/.env."
info "We will prompt for each value and validate the format."

mkdir -p "$SCRIPT_DIR/config"

SKIP_ENV=false
if [[ -f "$ENV_FILE" ]]; then
    success "config/.env already exists"
    if confirm "Reconfigure credentials from scratch?" "n"; then
        cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%s)"
        info "Backed up existing .env"
    else
        info "Keeping existing config/.env. You can edit it manually later."
        SKIP_ENV=true
    fi
fi

if [[ "$SKIP_ENV" == "false" ]]; then
    # Start from the example template
    if [[ -f "$ENV_EXAMPLE" ]]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
    else
        touch "$ENV_FILE"
    fi

    # --- QuickBooks Online ---
    echo ""
    echo -e "${BOLD}QuickBooks Online App Configuration${NC}"
    echo ""
    info "QBO Copilot needs an Intuit Developer app to connect to QuickBooks."
    info "You can use the shared WiseCopilots app (fastest setup) or register your own."
    echo ""
    echo -e "  ${GREEN}1)${NC} Use WiseCopilots shared app ${YELLOW}(recommended — fastest setup)${NC}"
    echo -e "  ${GREEN}2)${NC} Use your own Intuit Developer app"
    echo ""

    prompt_value "Choice [1/2]" qbo_app_choice "1"
    while [[ "$qbo_app_choice" != "1" && "$qbo_app_choice" != "2" ]]; do
        error "Please enter 1 or 2."
        prompt_value "Choice [1/2]" qbo_app_choice "1"
    done

    if [[ "$qbo_app_choice" == "1" ]]; then
        # Shared WiseCopilots app
        qbo_client_id="ABgPV5So1Mhy5VPC65mBDmAQ63Jyn8CeiI1ukbAKfchCGblsoS"
        qbo_client_secret="yONgG8x5bvzQPuYoZj0EHiuDubE6jHghLnZBGrHZ"
        success "Using WiseCopilots shared app credentials"
    else
        # Custom app
        info "Create an app at https://developer.intuit.com/app/developer/dashboard"
        info "You need the Client ID and Client Secret from your app's Keys tab."
        echo ""

        prompt_value "QBO Client ID" qbo_client_id
        while [[ -z "$qbo_client_id" ]]; do
            error "Client ID is required."
            prompt_value "QBO Client ID" qbo_client_id
        done

        prompt_value "QBO Client Secret" qbo_client_secret "" true
        while [[ -z "$qbo_client_secret" ]]; do
            error "Client Secret is required."
            prompt_value "QBO Client Secret" qbo_client_secret "" true
        done
    fi

    set_env_value "QBO_CLIENT_ID" "$qbo_client_id" "$ENV_FILE"
    set_env_value "QBO_CLIENT_SECRET" "$qbo_client_secret" "$ENV_FILE"

    prompt_value "QBO Environment (sandbox/production)" qbo_env "sandbox"
    while [[ "$qbo_env" != "sandbox" && "$qbo_env" != "production" ]]; do
        error "Must be 'sandbox' or 'production'."
        prompt_value "QBO Environment (sandbox/production)" qbo_env "sandbox"
    done
    set_env_value "QBO_ENVIRONMENT" "$qbo_env" "$ENV_FILE"
    success "QuickBooks Online credentials saved"

    # --- Anthropic ---
    echo ""
    echo -e "${BOLD}Anthropic API key${NC}"
    info "Powers the AI assistant. Get a key at https://console.anthropic.com/settings/keys"
    echo ""

    prompt_value "Anthropic API Key (starts with sk-ant-)" anthropic_key "" true
    while [[ ! "$anthropic_key" =~ ^sk-ant- ]]; do
        error "Key must start with 'sk-ant-'. Check your Anthropic dashboard."
        prompt_value "Anthropic API Key" anthropic_key "" true
    done
    set_env_value "ANTHROPIC_API_KEY" "$anthropic_key" "$ENV_FILE"
    success "Anthropic API key saved"

    # --- Slack ---
    echo ""
    echo -e "${BOLD}Slack Bot credentials${NC}"
    info "Create a Slack app at https://api.slack.com/apps using the manifest"
    info "in config/slack-app-manifest.json, then install it to your workspace."
    echo ""

    prompt_value "Slack Bot Token (starts with xoxb-)" slack_bot_token "" true
    while [[ ! "$slack_bot_token" =~ ^xoxb- ]]; do
        error "Bot Token must start with 'xoxb-'. Find it under OAuth & Permissions."
        prompt_value "Slack Bot Token" slack_bot_token "" true
    done
    set_env_value "SLACK_BOT_TOKEN" "$slack_bot_token" "$ENV_FILE"

    prompt_value "Slack App Token (starts with xapp-)" slack_app_token "" true
    while [[ ! "$slack_app_token" =~ ^xapp- ]]; do
        error "App Token must start with 'xapp-'. Generate one under Basic Information > App-Level Tokens."
        prompt_value "Slack App Token" slack_app_token "" true
    done
    set_env_value "SLACK_APP_TOKEN" "$slack_app_token" "$ENV_FILE"

    prompt_value "Slack Signing Secret" slack_signing_secret "" true
    while [[ -z "$slack_signing_secret" ]]; do
        error "Signing Secret is required. Find it under Basic Information."
        prompt_value "Slack Signing Secret" slack_signing_secret "" true
    done
    set_env_value "SLACK_SIGNING_SECRET" "$slack_signing_secret" "$ENV_FILE"
    success "Slack credentials saved"

    # --- Google Drive (optional) ---
    echo ""
    if confirm "Configure Google Drive integration? (optional -- used for document storage)" "n"; then
        echo -e "${BOLD}Google Drive credentials${NC}"
        info "Requires a GCP service account JSON key file."
        info "See: https://cloud.google.com/iam/docs/service-accounts-create"
        echo ""

        prompt_value "Path to service account JSON" gdrive_sa_path
        if [[ -n "$gdrive_sa_path" ]]; then
            if [[ ! -f "$gdrive_sa_path" ]]; then
                warn "File not found at '$gdrive_sa_path'. Saving anyway; fix the path in config/.env later."
            fi
            set_env_value "GOOGLE_SERVICE_ACCOUNT_PATH" "$gdrive_sa_path" "$ENV_FILE"

            prompt_value "Google Drive root folder ID" gdrive_folder_id
            if [[ -n "$gdrive_folder_id" ]]; then
                set_env_value "GOOGLE_DRIVE_ROOT_FOLDER_ID" "$gdrive_folder_id" "$ENV_FILE"
            fi
            success "Google Drive config saved"
        fi
    else
        info "Skipping Google Drive. You can add it later in config/.env."
    fi

    # --- SMTP (optional) ---
    echo ""
    if confirm "Configure SMTP for email notifications? (optional)" "n"; then
        echo -e "${BOLD}SMTP credentials${NC}"
        info "Used for sending email notifications (e.g., invoice reminders)."
        echo ""

        prompt_value "SMTP Host" smtp_host "smtp.gmail.com"
        set_env_value "SMTP_HOST" "$smtp_host" "$ENV_FILE"

        prompt_value "SMTP Port" smtp_port "587"
        set_env_value "SMTP_PORT" "$smtp_port" "$ENV_FILE"

        prompt_value "SMTP User (email address)" smtp_user
        if [[ -n "$smtp_user" ]]; then
            set_env_value "SMTP_USER" "$smtp_user" "$ENV_FILE"
        fi

        prompt_value "SMTP Password (app password)" smtp_password "" true
        if [[ -n "$smtp_password" ]]; then
            set_env_value "SMTP_PASSWORD" "$smtp_password" "$ENV_FILE"
        fi
        success "SMTP config saved"
    else
        info "Skipping SMTP. You can add it later in config/.env."
    fi

    echo ""
    success "All credentials written to config/.env"
fi

# ===========================================================================
# Step 4: QBO OAuth flow
# ===========================================================================
print_step 4 "QuickBooks Online Authorization"
info "QBO Copilot needs OAuth tokens to access your QuickBooks data."
info "This will open your browser to authorize the app with Intuit."

mkdir -p "$TOKENS_DIR"

SKIP_OAUTH=false
if [[ -f "$TOKENS_DIR/default.json" ]]; then
    success "OAuth tokens already exist at config/tokens/default.json"
    if confirm "Re-authorize with QuickBooks?" "n"; then
        info "Starting OAuth flow..."
    else
        info "Keeping existing tokens."
        SKIP_OAUTH=true
    fi
fi

if [[ "$SKIP_OAUTH" == "false" ]]; then
    info "Starting local OAuth callback server and opening browser..."
    info "Sign in to your Intuit account and authorize the app."
    echo ""

    # Source .env so the oauth script can read credentials
    set +u
    # shellcheck disable=SC1090
    source <(grep -v '^\s*#' "$ENV_FILE" | sed 's/^/export /')
    set -u

    if python3 "$SCRIPT_DIR/qbo/oauth.py"; then
        success "OAuth authorization complete"
    else
        error "OAuth flow failed."
        info "Make sure QBO_CLIENT_ID and QBO_CLIENT_SECRET are correct in config/.env"
        info "Also ensure http://localhost:8080/callback is set as a redirect URI"
        info "in your Intuit developer app settings."
        info ""
        info "You can retry this step by running:  python3 qbo/oauth.py"
        if ! confirm "Continue setup anyway?"; then
            exit 1
        fi
    fi
fi

# ===========================================================================
# Step 5: Client configuration
# ===========================================================================
print_step 5 "Client Configuration"
info "QBO Copilot supports multiple QBO companies (multi-tenant)."
info "We will create config/clients.yaml with your first company."

SKIP_CLIENTS=false
if [[ -f "$CLIENTS_YAML" ]]; then
    success "config/clients.yaml already exists"
    if confirm "Overwrite with a new client config?" "n"; then
        cp "$CLIENTS_YAML" "${CLIENTS_YAML}.bak.$(date +%s)"
        info "Backed up existing clients.yaml"
    else
        info "Keeping existing client configuration."
        SKIP_CLIENTS=true
    fi
fi

if [[ "$SKIP_CLIENTS" == "false" ]]; then
    # Read realm_id from the token file
    REALM_ID=""
    if [[ -f "$TOKENS_DIR/default.json" ]]; then
        REALM_ID=$(python3 -c "import json; print(json.load(open('$TOKENS_DIR/default.json')).get('realmId', ''))" 2>/dev/null || echo "")
    fi

    if [[ -z "$REALM_ID" ]]; then
        warn "Could not read realm_id from tokens. You will need to enter it manually."
        prompt_value "QBO Company (Realm) ID" REALM_ID
        while [[ -z "$REALM_ID" ]]; do
            error "Realm ID is required. Find it in your QBO URL or Intuit developer dashboard."
            prompt_value "QBO Company (Realm) ID" REALM_ID
        done
    else
        success "Detected QBO company realm_id: $REALM_ID"
    fi

    prompt_value "Display name for this company" client_name "My Company"
    prompt_value "Primary contact email" client_email ""
    prompt_value "Slack channel for this company (e.g., #qbo-general)" client_channel "#qbo-general"

    # Determine environment from .env
    client_env="sandbox"
    if [[ -f "$ENV_FILE" ]]; then
        client_env=$(grep -E "^QBO_ENVIRONMENT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "sandbox")
        client_env=${client_env:-sandbox}
    fi

    cat > "$CLIENTS_YAML" << YAML
# QBO Copilot - Client Companies Configuration
#
# Each client represents a QBO company that the CPA has access to.
# The agent can switch between clients to query different companies.

clients:
  - name: "$client_name"
    realm_id: "$REALM_ID"
    primary_contact: "$client_email"
    slack_channel: "$client_channel"
    metadata:
      environment: $client_env
      notes: "Added by setup.sh on $(date +%Y-%m-%d)"
YAML

    success "config/clients.yaml created with company '$client_name'"
fi

# ===========================================================================
# Step 6: Validation
# ===========================================================================
print_step 6 "Connection Validation"
info "Testing each integration to make sure everything is wired up correctly."

# Source .env for validation commands
set +u
# shellcheck disable=SC1090
source <(grep -v '^\s*#' "$ENV_FILE" | sed 's/^/export /')
set -u

validation_passed=true

# --- Test QBO connection ---
echo ""
info "Testing QuickBooks Online API..."
if python3 "$SCRIPT_DIR/qbo/client.py" accounts > /dev/null 2>&1; then
    account_count=$(python3 "$SCRIPT_DIR/qbo/client.py" accounts 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "?")
    success "QBO API connected -- found $account_count accounts"
else
    error "QBO API connection failed."
    info "Check your OAuth tokens and QBO_CLIENT_ID / QBO_CLIENT_SECRET."
    info "Try re-authorizing:  python3 qbo/oauth.py"
    validation_passed=false
fi

# --- Test Slack auth ---
echo ""
info "Testing Slack Bot Token..."
slack_bot_token_val=${SLACK_BOT_TOKEN:-}
if [[ -n "$slack_bot_token_val" ]]; then
    slack_auth_result=$(python3 -c "
import requests, os
token = os.environ.get('SLACK_BOT_TOKEN', '')
r = requests.post('https://slack.com/api/auth.test', headers={'Authorization': f'Bearer {token}'})
data = r.json()
if data.get('ok'):
    print('ok:' + data.get('team', 'unknown'))
else:
    print('fail:' + data.get('error', 'unknown'))
" 2>/dev/null || echo "fail:exception")

    if [[ "$slack_auth_result" == ok:* ]]; then
        team_name="${slack_auth_result#ok:}"
        success "Slack connected to workspace: $team_name"
    else
        slack_error="${slack_auth_result#fail:}"
        error "Slack auth failed: $slack_error"
        info "Check SLACK_BOT_TOKEN in config/.env"
        validation_passed=false
    fi
else
    warn "SLACK_BOT_TOKEN not set. Skipping Slack validation."
    validation_passed=false
fi

# --- Test Anthropic API ---
echo ""
info "Testing Anthropic API key..."
anthropic_key_val=${ANTHROPIC_API_KEY:-}
if [[ -n "$anthropic_key_val" ]]; then
    anthropic_result=$(python3 -c "
import anthropic, os
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
resp = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=16,
    messages=[{'role': 'user', 'content': 'Reply with the word OK only.'}]
)
print('ok')
" 2>/dev/null || echo "fail")

    if [[ "$anthropic_result" == "ok" ]]; then
        success "Anthropic API key is valid"
    else
        error "Anthropic API call failed."
        info "Check ANTHROPIC_API_KEY in config/.env"
        info "Make sure the key starts with sk-ant- and has not expired."
        validation_passed=false
    fi
else
    warn "ANTHROPIC_API_KEY not set. Skipping Anthropic validation."
    validation_passed=false
fi

# --- Validation summary ---
echo ""
if [[ "$validation_passed" == "true" ]]; then
    success "All validations passed!"
else
    warn "Some validations failed. The bot may not work correctly."
    info "Fix the issues above and re-run:  ./setup.sh"
fi

# ===========================================================================
# Step 7: Summary
# ===========================================================================
print_step 7 "Setup Summary"

echo -e "  ${GREEN}Config file:${NC}     config/.env"
echo -e "  ${GREEN}Client config:${NC}   config/clients.yaml"
echo -e "  ${GREEN}OAuth tokens:${NC}    config/tokens/"
echo -e "  ${GREEN}Virtual env:${NC}     venv/"
echo ""
echo -e "  ${DIM}To activate the virtualenv in a new terminal:${NC}"
echo -e "  ${BOLD}  source venv/bin/activate${NC}"
echo ""
echo -e "  ${DIM}Useful commands:${NC}"
echo -e "    ${BOLD}python3 integrations/slack/bot.py${NC}  -- Start the Slack bot"
echo -e "    ${BOLD}python3 agent/main.py${NC}              -- Interactive CLI agent"
echo -e "    ${BOLD}python3 qbo/client.py accounts${NC}     -- Quick QBO test"
echo -e "    ${BOLD}python3 -m pytest tests/ -v${NC}        -- Run test suite"

# ===========================================================================
# Step 8: Launch
# ===========================================================================
print_step 8 "Launch"

if confirm "Start the Slack bot now?"; then
    echo ""
    info "Starting QBO Copilot Slack bot..."
    info "Press Ctrl+C to stop."
    echo ""
    exec python3 "$SCRIPT_DIR/integrations/slack/bot.py"
else
    echo ""
    success "Setup complete! Start the bot anytime with:"
    echo ""
    echo -e "    ${BOLD}source venv/bin/activate${NC}"
    echo -e "    ${BOLD}python3 integrations/slack/bot.py${NC}"
    echo ""
    echo -e "${DIM}Happy accounting!${NC}"
fi
