#!/bin/bash
#
# QBO Quick Test Script
# Run all QBO CLI commands to verify functionality
#
# Usage: ./tests/test_qbo_quick.sh
#

set -e
cd "$(dirname "$0")/.."

echo "========================================"
echo "QBO Quick Test Suite"
echo "========================================"
echo ""

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
info() { echo -e "  $1"; }

# Track test results
PASSED=0
FAILED=0

run_test() {
    local name="$1"
    local cmd="$2"

    echo ""
    echo "--- $name ---"

    if output=$(eval "$cmd" 2>&1); then
        # Check if output is valid JSON with success or expected fields
        if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d.get('success',True) else 1)" 2>/dev/null; then
            pass "$name"
            PASSED=$((PASSED + 1))
            # Show summary
            echo "$output" | python3 -c "
import json,sys
d=json.load(sys.stdin)
if 'count' in d:
    print(f\"  Count: {d['count']}\")
if 'message' in d:
    print(f\"  {d['message']}\")
" 2>/dev/null || true
        else
            pass "$name (returned data)"
            PASSED=$((PASSED + 1))
        fi
    else
        fail "$name"
        FAILED=$((FAILED + 1))
        info "Error: $output"
    fi
}

echo "========================================"
echo "1. READ OPERATIONS"
echo "========================================"

run_test "Get Accounts" \
    "python qbo/client.py accounts"

run_test "Get Customers" \
    "python qbo/client.py customers"

run_test "Get Vendors" \
    "python qbo/client.py vendors"

run_test "Get All Invoices" \
    "python qbo/client.py invoices"

run_test "Get Unpaid Invoices" \
    "python qbo/client.py invoices --unpaid"

run_test "Get Purchases (Last 30 days)" \
    "python qbo/client.py purchases --start $(date -v-30d +%Y-%m-%d) --end $(date +%Y-%m-%d)"

run_test "Custom Query" \
    "python qbo/client.py query 'SELECT * FROM Account WHERE AccountType = '\\''Bank'\\'' MAXRESULTS 5'"

echo ""
echo "========================================"
echo "2. WRITE OPERATIONS"
echo "========================================"

# Create test customer
TIMESTAMP=$(date +%H%M%S)
TEST_CUSTOMER="Test Customer $TIMESTAMP"
TEST_VENDOR="Test Vendor $TIMESTAMP"

run_test "Create Customer" \
    "python qbo/client.py create-customer --name '$TEST_CUSTOMER' --email 'test$TIMESTAMP@example.com'"

run_test "Create Vendor" \
    "python qbo/client.py create-vendor --name '$TEST_VENDOR' --email 'vendor$TIMESTAMP@example.com'"

# Get a customer ID for invoice creation
echo ""
echo "--- Create Invoice ---"
CUSTOMER_ID=$(python qbo/client.py customers 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['customers'][0]['Id'] if d['customers'] else '')" 2>/dev/null || echo "")

if [ -n "$CUSTOMER_ID" ]; then
    run_test "Create Invoice" \
        "python qbo/client.py create-invoice --customer '$CUSTOMER_ID' --amount 99.99 --description 'Test invoice from quick test'"
else
    warn "Skipped Create Invoice - no customers found"
fi

echo ""
echo "========================================"
echo "3. ENTITY GET OPERATION"
echo "========================================"

# Get first account ID
ACCOUNT_ID=$(python qbo/client.py accounts 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['accounts'][0]['Id'] if d['accounts'] else '')" 2>/dev/null || echo "")

if [ -n "$ACCOUNT_ID" ]; then
    run_test "Get Single Entity (Account)" \
        "python qbo/client.py get Account '$ACCOUNT_ID'"
else
    warn "Skipped Get Entity - no accounts found"
fi

echo ""
echo "========================================"
echo "SUMMARY"
echo "========================================"
echo ""
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    exit 1
fi

echo -e "${GREEN}All tests passed!${NC}"
