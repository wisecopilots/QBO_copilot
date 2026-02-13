# Google Drive Integration (Optional)

QBO Copilot can optionally integrate with Google Drive to create a structured document vault for each client company. Scanned receipts, invoices, bills, and other financial documents are automatically filed into organized folders.

This integration is **optional**. QBO Copilot works without it -- receipt scanning and all QBO features function independently.

---

## Prerequisites

- A Google Cloud Platform (GCP) account
- A Google Drive account with enough storage for client documents
- Admin access to create GCP projects and service accounts

## Step 1: Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** at the top, then **New Project**
3. Name it something descriptive (e.g., "QBO Copilot" or "CPA Document Vault")
4. Click **Create**
5. Wait for the project to be created, then select it

## Step 2: Enable the Google Drive API

1. In your project, navigate to **APIs & Services** > **Library**
2. Search for **Google Drive API**
3. Click on the result and click **Enable**

## Step 3: Create a Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Fill in:
   - **Name:** `qbo-copilot-drive`
   - **Description:** "Service account for QBO Copilot document vault"
4. Click **Create and Continue**
5. Skip the optional role and user access steps
6. Click **Done**

## Step 4: Download the Service Account Key

1. In the Credentials list, click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key** > **Create new key**
4. Select **JSON** format
5. Click **Create**
6. Save the downloaded JSON file to your project:

```bash
mv ~/Downloads/your-project-*.json config/google-service-account.json
```

**Important:** This file contains sensitive credentials. Never commit it to version control. It should already be covered by `.gitignore`.

## Step 5: Create and Share the Root Folder

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder (e.g., "CPA Clients")
3. Right-click the folder and select **Share**
4. Find the service account email address in your JSON key file (the `client_email` field -- it looks like `qbo-copilot-drive@your-project.iam.gserviceaccount.com`)
5. Add that email with **Editor** access
6. Click **Send** (or **Share**)
7. Copy the folder ID from the URL:
   - URL format: `https://drive.google.com/drive/folders/1ABC123XYZ...`
   - The folder ID is: `1ABC123XYZ...` (everything after `/folders/`)

## Step 6: Configure Environment Variables

Add these to your `config/.env` file:

```bash
# Google Drive Integration
GOOGLE_SERVICE_ACCOUNT_PATH=config/google-service-account.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=1ABC123XYZ_your_folder_id_here
```

---

## Folder Structure

When a new client is onboarded, QBO Copilot automatically creates a folder structure under the root folder:

```
CPA Clients/
  Acme Corp/
    Tax Returns/
    Financial Statements/
    Bank Statements/
    Receipts/
    Invoices/
    Bills/
    Payroll/
    Legal/
    Correspondence/
  Beta Industries/
    Tax Returns/
    Financial Statements/
    ...
```

Each category folder can contain period subfolders (e.g., "2025", "Q1 2026") that are created as documents are filed.

The `Receipts`, `Invoices`, and `Bills` folders are used by the receipt scanning feature to automatically file scanned documents after they are approved.

## Testing the Connection

You can verify the integration is working with a quick Python test:

```python
from integrations.google_drive import GoogleDriveClient, is_drive_configured

if is_drive_configured():
    drive = GoogleDriveClient()
    files = drive.list_folder(drive.root_folder_id)
    print(f"Connected. Found {len(files)} items in root folder.")
else:
    print("Google Drive is not configured.")
```

Or create a test client folder:

```python
drive = GoogleDriveClient()
folder_id = drive.create_client_folder("Test Client")
print(f"Created folder: {folder_id}")
```

---

## How It Works with Receipt Scanning

When Google Drive is configured, the receipt scanning workflow extends to include automatic filing:

1. User uploads a receipt image to the Slack DM
2. User classifies the document type (receipt, invoice, bill)
3. Claude Vision extracts structured data
4. A review card is shown in Slack
5. When the document is approved, it is uploaded to the appropriate Google Drive folder
6. A link to the filed document is included in the confirmation message

Without Google Drive configured, everything up through step 4 still works -- documents are just not filed to Drive.

---

## Security Notes

1. **Service Account Key:** Keep the JSON credentials file secure. It grants full access to any Drive folders shared with the service account.

2. **Minimal Access:** The service account only has access to folders explicitly shared with it. It cannot access other files in your Drive.

3. **User Access:** To let team members view filed documents, either:
   - Share the root folder (or subfolders) with their Google accounts
   - Use the shareable links generated by the bot

4. **Audit Trail:** All file operations (uploads, folder creation) are logged in the SQLite `audit_log` table.

---

## Troubleshooting

### "File not found" errors

- Verify the root folder ID is correct in `config/.env`
- Confirm the folder is shared with the service account email (with Editor access)

### "Permission denied" errors

- Check that the service account has Editor access to the root folder
- Verify the Google Drive API is enabled in your GCP project
- Make sure you are using the correct GCP project

### "Credentials not found" or "Could not load service account"

- Verify `GOOGLE_SERVICE_ACCOUNT_PATH` points to the correct file
- The path can be relative (from the project root) or absolute
- Confirm the JSON file exists and is readable

### "Drive API has not been used in project" error

- Go to the GCP console and enable the Google Drive API for your project
- It may take a minute or two after enabling before it works

### Files not appearing in Drive

- Check the bot logs for upload errors
- Verify the service account has write access to the target folder
- Ensure the `GOOGLE_DRIVE_ROOT_FOLDER_ID` environment variable is set
