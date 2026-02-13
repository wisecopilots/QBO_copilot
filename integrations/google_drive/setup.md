# Google Drive Integration Setup

This guide explains how to set up Google Drive integration for the CPA document vault.

## Prerequisites

- Google Cloud Platform account
- Access to create projects and service accounts

## Setup Steps

### 1. Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it something like "QBO Copilot" or "CPA Document Vault"
4. Click "Create"

### 2. Enable the Google Drive API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on it and click "Enable"

### 3. Create a Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Name: `qbo-copilot-drive`
4. Description: "Service account for QBO Copilot document vault"
5. Click "Create and Continue"
6. Skip the optional steps (no role needed for Drive)
7. Click "Done"

### 4. Create and Download Credentials

1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Choose "JSON" format
5. Click "Create"
6. Save the downloaded JSON file securely (e.g., `config/google-service-account.json`)

**IMPORTANT:** Never commit this file to version control!

### 5. Create the Root Folder in Google Drive

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder (e.g., "CPA Clients")
3. Right-click the folder → "Share"
4. Add the service account email (found in your credentials JSON as `client_email`)
5. Give it "Editor" access
6. Copy the folder ID from the URL:
   - URL: `https://drive.google.com/drive/folders/1ABC123XYZ...`
   - Folder ID: `1ABC123XYZ...`

### 6. Configure Environment Variables

Add these to your `.env` file:

```bash
# Google Drive Integration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/config/google-service-account.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=1ABC123XYZ...
```

### 7. Install Dependencies

```bash
pip install google-api-python-client google-auth
```

Or add to requirements.txt:
```
google-api-python-client>=2.0
google-auth>=2.0
```

## Folder Structure

When a new client is onboarded, the following folder structure is created:

```
CPA Clients/
└── {Client Name}/
    ├── Tax Returns/
    ├── Financial Statements/
    ├── Bank Statements/
    ├── Payroll/
    ├── Legal/
    └── Correspondence/
```

Each category folder can have period subfolders (e.g., "2024", "Q1 2025").

## Usage Example

```python
from integrations.google_drive import GoogleDriveClient

# Initialize client
drive = GoogleDriveClient()

# Create client folder structure
folder_id = drive.create_client_folder("Acme Corp")

# Upload a file
with open("statement.pdf", "rb") as f:
    file_id = drive.upload_file(
        folder_id=folder_id,
        file_data=f,
        filename="January_2025_Bank_Statement.pdf",
        mime_type="application/pdf"
    )

# Get shareable link
link = drive.get_file_link(file_id)
print(f"View file: {link}")
```

## Security Notes

1. **Service Account Key:** Keep the JSON credentials file secure. Never commit it to version control.

2. **Folder Sharing:** The service account only has access to folders explicitly shared with it.

3. **User Access:** To let users view files, either:
   - Share individual files/folders with them
   - Use the web view links (requires Google account)

4. **Audit Trail:** All file operations are logged in the `audit_log` table.

## Troubleshooting

### "File not found" errors
- Ensure the folder is shared with the service account email
- Check the folder ID is correct

### "Permission denied" errors
- Verify the service account has Editor access to the root folder
- Check that the Drive API is enabled in GCP

### "Credentials not found"
- Verify the `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Ensure the JSON file exists and is readable

## Testing the Integration

```python
from integrations.google_drive import GoogleDriveClient, is_drive_configured

# Check if configured
if is_drive_configured():
    drive = GoogleDriveClient()

    # Test by listing root folder
    files = drive.list_folder(drive.root_folder_id)
    print(f"Found {len(files)} items in root folder")
else:
    print("Google Drive not configured")
```
