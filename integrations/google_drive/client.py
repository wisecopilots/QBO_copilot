"""
Google Drive Client

Document vault integration for CPA client files.
Uses service account authentication for server-to-server access.
"""

import os
import io
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, BinaryIO

logger = logging.getLogger(__name__)

# Try to import Google libraries - gracefully handle if not installed
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google API libraries not installed. Run: pip install google-api-python-client google-auth")


SCOPES = ['https://www.googleapis.com/auth/drive']


class GoogleDriveClient:
    """
    Google Drive API client for document vault operations.

    Uses service account authentication. Requires:
    - GOOGLE_APPLICATION_CREDENTIALS env var pointing to service account JSON
    - GOOGLE_DRIVE_ROOT_FOLDER_ID env var for the parent folder
    """

    def __init__(self, credentials_path: Optional[str] = None, root_folder_id: Optional[str] = None):
        """
        Initialize the Drive client.

        Args:
            credentials_path: Path to service account JSON (or use GOOGLE_APPLICATION_CREDENTIALS)
            root_folder_id: Root folder ID for client folders (or use GOOGLE_DRIVE_ROOT_FOLDER_ID)
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. "
                "Run: pip install google-api-python-client google-auth"
            )

        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.root_folder_id = root_folder_id or os.getenv('GOOGLE_DRIVE_ROOT_FOLDER_ID')

        if not self.credentials_path:
            raise ValueError("No credentials path provided. Set GOOGLE_APPLICATION_CREDENTIALS or pass credentials_path")

        if not Path(self.credentials_path).exists():
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")

        self._service = None

    @property
    def service(self):
        """Lazy-load the Drive service"""
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=SCOPES
            )
            self._service = build('drive', 'v3', credentials=credentials)
        return self._service

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Drive.

        Args:
            name: Folder name
            parent_id: Parent folder ID (defaults to root_folder_id)

        Returns:
            Created folder ID
        """
        parent = parent_id or self.root_folder_id
        parents = [parent] if parent else []

        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': parents
        }

        folder = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        logger.info(f"Created folder '{name}' with ID: {folder.get('id')}")
        return folder.get('id')

    def create_client_folder(self, client_name: str) -> str:
        """
        Create the standard folder structure for a client.

        Creates:
        - {client_name}/
          - Tax Returns/
          - Financial Statements/
          - Bank Statements/
          - Payroll/
          - Legal/
          - Correspondence/

        Args:
            client_name: Client display name

        Returns:
            Root client folder ID
        """
        # Create main client folder
        client_folder_id = self.create_folder(client_name)

        # Create standard subfolders
        subfolders = [
            'Tax Returns',
            'Financial Statements',
            'Bank Statements',
            'Payroll',
            'Legal',
            'Correspondence',
            'Receipts',
            'Invoices',
            'Bills',
        ]

        for subfolder in subfolders:
            self.create_folder(subfolder, client_folder_id)

        logger.info(f"Created client folder structure for '{client_name}'")
        return client_folder_id

    def create_period_subfolder(self, parent_id: str, period: str) -> str:
        """
        Create a period subfolder (e.g., "2024", "Q1 2025").

        Args:
            parent_id: Parent folder ID
            period: Period name

        Returns:
            Created folder ID
        """
        return self.create_folder(period, parent_id)

    def upload_file(
        self,
        folder_id: str,
        file_data: BinaryIO,
        filename: str,
        mime_type: str = 'application/octet-stream'
    ) -> str:
        """
        Upload a file to a folder.

        Args:
            folder_id: Target folder ID
            file_data: File data as bytes or file-like object
            filename: Name for the file
            mime_type: MIME type of the file

        Returns:
            Uploaded file ID
        """
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }

        media = MediaIoBaseUpload(
            file_data,
            mimetype=mime_type,
            resumable=True
        )

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()

        logger.info(f"Uploaded file '{filename}' with ID: {file.get('id')}")
        return file.get('id')

    def upload_bytes(
        self,
        folder_id: str,
        data: bytes,
        filename: str,
        mime_type: str = 'application/octet-stream'
    ) -> str:
        """
        Upload bytes data as a file.

        Args:
            folder_id: Target folder ID
            data: File data as bytes
            filename: Name for the file
            mime_type: MIME type

        Returns:
            Uploaded file ID
        """
        return self.upload_file(folder_id, io.BytesIO(data), filename, mime_type)

    def get_file_link(self, file_id: str) -> str:
        """
        Get the web view link for a file.

        Args:
            file_id: File ID

        Returns:
            Web view URL
        """
        file = self.service.files().get(
            fileId=file_id,
            fields='webViewLink'
        ).execute()
        return file.get('webViewLink', '')

    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            file_id: File ID

        Returns:
            File metadata dict
        """
        file = self.service.files().get(
            fileId=file_id,
            fields='id, name, mimeType, size, createdTime, modifiedTime, webViewLink, parents'
        ).execute()
        return file

    def list_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        List files in a folder.

        Args:
            folder_id: Folder ID

        Returns:
            List of file metadata dicts
        """
        results = self.service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            pageSize=100,
            fields="files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)"
        ).execute()

        return results.get('files', [])

    def search_files(
        self,
        query: str,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for files.

        Args:
            query: Search query (file name)
            folder_id: Limit to folder (optional)
            mime_type: Filter by MIME type (optional)

        Returns:
            List of matching files
        """
        q_parts = [f"name contains '{query}'", "trashed = false"]

        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        if mime_type:
            q_parts.append(f"mimeType = '{mime_type}'")

        q = " and ".join(q_parts)

        results = self.service.files().list(
            q=q,
            pageSize=50,
            fields="files(id, name, mimeType, size, webViewLink, parents)"
        ).execute()

        return results.get('files', [])

    def download_file(self, file_id: str) -> bytes:
        """
        Download a file's content.

        Args:
            file_id: File ID

        Returns:
            File content as bytes
        """
        request = self.service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue()

    def move_file(self, file_id: str, new_parent_id: str) -> bool:
        """
        Move a file to a different folder.

        Args:
            file_id: File ID to move
            new_parent_id: Target folder ID

        Returns:
            Success status
        """
        # Get current parents
        file = self.service.files().get(
            fileId=file_id,
            fields='parents'
        ).execute()

        previous_parents = ",".join(file.get('parents', []))

        # Move to new parent
        self.service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()

        logger.info(f"Moved file {file_id} to folder {new_parent_id}")
        return True

    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """
        Delete a file (move to trash by default).

        Args:
            file_id: File ID
            permanent: If True, permanently delete (not recoverable)

        Returns:
            Success status
        """
        if permanent:
            self.service.files().delete(fileId=file_id).execute()
        else:
            self.service.files().update(
                fileId=file_id,
                body={'trashed': True}
            ).execute()

        logger.info(f"Deleted file {file_id} (permanent={permanent})")
        return True

    def share_folder(self, folder_id: str, email: str, role: str = 'reader') -> bool:
        """
        Share a folder with a user.

        Args:
            folder_id: Folder ID
            email: Email address to share with
            role: Permission role ('reader', 'writer', 'commenter')

        Returns:
            Success status
        """
        permission = {
            'type': 'user',
            'role': role,
            'emailAddress': email
        }

        self.service.permissions().create(
            fileId=folder_id,
            body=permission,
            sendNotificationEmail=True
        ).execute()

        logger.info(f"Shared folder {folder_id} with {email} as {role}")
        return True

    def get_folder_by_name(self, name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find a folder by name.

        Args:
            name: Folder name
            parent_id: Parent folder to search in

        Returns:
            Folder ID if found, None otherwise
        """
        parent = parent_id or self.root_folder_id
        q_parts = [
            f"name = '{name}'",
            "mimeType = 'application/vnd.google-apps.folder'",
            "trashed = false"
        ]

        if parent:
            q_parts.append(f"'{parent}' in parents")

        q = " and ".join(q_parts)

        results = self.service.files().list(
            q=q,
            pageSize=1,
            fields="files(id)"
        ).execute()

        files = results.get('files', [])
        return files[0]['id'] if files else None

    def ensure_folder_structure(
        self,
        client_name: str,
        doc_category: str,
        period: Optional[str] = None
    ) -> str:
        """
        Ensure folder structure exists and return target folder ID.

        Creates client folder and subfolders if they don't exist.

        Args:
            client_name: Client display name
            doc_category: Document category (e.g., "Bank Statements")
            period: Optional period subfolder (e.g., "2024")

        Returns:
            Target folder ID for uploading
        """
        # Find or create client folder
        client_folder_id = self.get_folder_by_name(client_name)
        if not client_folder_id:
            client_folder_id = self.create_client_folder(client_name)

        # Find or create category subfolder
        category_folder_id = self.get_folder_by_name(doc_category, client_folder_id)
        if not category_folder_id:
            category_folder_id = self.create_folder(doc_category, client_folder_id)

        # If period specified, create period subfolder
        if period:
            period_folder_id = self.get_folder_by_name(period, category_folder_id)
            if not period_folder_id:
                period_folder_id = self.create_folder(period, category_folder_id)
            return period_folder_id

        return category_folder_id


# Utility functions for common operations

def get_drive_client() -> Optional[GoogleDriveClient]:
    """Get a configured Drive client, or None if not available"""
    try:
        return GoogleDriveClient()
    except (ImportError, ValueError, FileNotFoundError) as e:
        logger.warning(f"Could not initialize Google Drive client: {e}")
        return None


def is_drive_configured() -> bool:
    """Check if Google Drive integration is configured"""
    if not GOOGLE_AVAILABLE:
        return False

    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path or not Path(creds_path).exists():
        return False

    return True
