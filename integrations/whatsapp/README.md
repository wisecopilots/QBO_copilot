# WhatsApp Business API Integration

This document covers the application process and setup for WhatsApp Business API integration with CPA Copilot.

## Application Process

### Prerequisites
1. A Facebook Business Manager account
2. A registered business (legal entity)
3. A phone number dedicated to WhatsApp Business (cannot be used with regular WhatsApp)
4. Business verification documents

### Step 1: Create Meta Developer Account
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Sign up or log in with Facebook account
3. Accept developer terms

### Step 2: Create App in Meta Developer Portal
1. Go to My Apps → Create App
2. Select "Business" as app type
3. Enter app name (e.g., "CPA Copilot WhatsApp")
4. Select Business Manager account

### Step 3: Add WhatsApp Product
1. In your app dashboard, click "Add Product"
2. Select "WhatsApp" and click "Set Up"
3. This creates a WhatsApp Business Account (WABA)

### Step 4: Business Verification
**Required for production access. This is the main bottleneck.**

Documents typically needed:
- Business registration certificate
- Tax ID / EIN
- Utility bill or bank statement (for address verification)
- Official business website

Timeline: 2-5 business days (can take longer)

### Step 5: Add Phone Number
1. In WhatsApp settings, go to "Phone Numbers"
2. Click "Add Phone Number"
3. Enter your business phone number
4. Verify via SMS or voice call

**Important**: This number becomes dedicated to WhatsApp Business API and can no longer use regular WhatsApp.

### Step 6: Get API Credentials
After verification, you'll have access to:
- Phone Number ID
- WhatsApp Business Account ID
- Permanent Access Token

## Technical Setup

### Environment Variables
```bash
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_waba_id
```

### Webhook Configuration
1. Create a webhook endpoint (e.g., `/webhook/whatsapp`)
2. In Meta Developer Portal, configure webhook URL
3. Subscribe to message events

### Message Templates
For outbound messages (you initiating), you need pre-approved templates:
1. Go to WhatsApp Manager → Message Templates
2. Create template with variables
3. Submit for approval (24-48 hours)
4. Use template for outbound messages

**Note**: Replies within 24 hours of user message don't require templates.

## Timeline Estimate

| Step | Duration |
|------|----------|
| Developer account setup | Same day |
| App creation | Same day |
| Business verification | 2-5 days |
| Phone number setup | Same day |
| Message template approval | 1-2 days |
| **Total** | **3-7 days** |

## Costs

### Meta/WhatsApp Fees
- First 1,000 conversations/month: Free
- Beyond 1,000: ~$0.005-0.08 per conversation (varies by country)

### Phone Number
- You provide the number (existing business line or new)
- Some providers offer virtual numbers for ~$5-15/month

## Alternative: WhatsApp Cloud API (Easier Start)

For testing and development, use Cloud API:
1. No business verification required initially
2. Free test phone number provided
3. Limited to sending to verified numbers only

This lets you develop while waiting for business verification.

## Code Structure

```
integrations/whatsapp/
├── README.md           # This file
├── webhook.py          # Webhook handler
├── client.py           # WhatsApp API client
└── templates.py        # Message template helpers
```

## Next Steps

1. [ ] Create Meta Developer account
2. [ ] Create app with WhatsApp product
3. [ ] Start business verification process
4. [ ] Set up test environment with Cloud API
5. [ ] Implement webhook handler
6. [ ] Create message templates
7. [ ] Test with verified numbers

## Resources

- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Business Verification Guide](https://www.facebook.com/business/help/2058515294227817)
- [Message Template Guidelines](https://developers.facebook.com/docs/whatsapp/message-templates)
- [Pricing](https://developers.facebook.com/docs/whatsapp/pricing)
