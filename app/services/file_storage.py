"""
File storage service for document management
"""
import os
import aiofiles
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod
from app.core.config import settings


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def save_file(self, file_content: bytes, file_path: str) -> str:
        """Save file content to storage"""
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve file content from storage"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in storage"""
        pass


class LocalFileStorage(StorageBackend):
    """Local filesystem storage backend"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, file_path: str) -> Path:
        """Get full filesystem path"""
        return self.base_path / file_path
    
    async def save_file(self, file_content: bytes, file_path: str) -> str:
        """Save file to local filesystem"""
        full_path = self._get_full_path(file_path)
        
        # Create directory if it doesn't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(full_path, 'wb') as f:
            await f.write(file_content)
        
        return str(full_path)
    
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve file from local filesystem"""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            full_path = self._get_full_path(file_path)
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in local filesystem"""
        full_path = self._get_full_path(file_path)
        return full_path.exists()


class CloudStorage(StorageBackend):
    """Cloud storage backend (placeholder for future implementation)"""
    
    async def save_file(self, file_content: bytes, file_path: str) -> str:
        """Save file to cloud storage"""
        # TODO: Implement cloud storage (S3, GCS, etc.)
        raise NotImplementedError("Cloud storage not implemented yet")
    
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve file from cloud storage"""
        # TODO: Implement cloud storage retrieval
        raise NotImplementedError("Cloud storage not implemented yet")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from cloud storage"""
        # TODO: Implement cloud storage deletion
        raise NotImplementedError("Cloud storage not implemented yet")
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in cloud storage"""
        # TODO: Implement cloud storage existence check
        raise NotImplementedError("Cloud storage not implemented yet")


class FileStorageService:
    """Main file storage service with backend abstraction"""
    
    def __init__(self, backend: Optional[StorageBackend] = None):
        if backend is None:
            # Default to local storage
            self.backend = LocalFileStorage(settings.UPLOAD_DIR)
        else:
            self.backend = backend
    
    def _generate_file_path(self, document_id: str, filename: str) -> str:
        """Generate storage path for document"""
        # Organize files by document ID to avoid conflicts
        safe_filename = self._sanitize_filename(filename)
        return f"{document_id}/{safe_filename}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove or replace unsafe characters
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in '.-_':
                safe_chars.append(char)
            else:
                safe_chars.append('_')
        
        return ''.join(safe_chars)
    
    async def save_document(
        self, 
        file_content: bytes, 
        document_id: str, 
        filename: str
    ) -> str:
        """
        Save document to storage
        
        Args:
            file_content: Raw file bytes
            document_id: Unique document identifier
            filename: Original filename
            
        Returns:
            Storage path where file was saved
        """
        file_path = self._generate_file_path(document_id, filename)
        storage_path = await self.backend.save_file(file_content, file_path)
        return storage_path
    
    async def get_document(self, document_id: str, filename: str) -> bytes:
        """
        Retrieve document from storage
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            
        Returns:
            File content as bytes
        """
        file_path = self._generate_file_path(document_id, filename)
        return await self.backend.get_file(file_path)
    
    async def delete_document(self, document_id: str, filename: Optional[str] = None) -> bool:
        """
        Delete document from storage
        
        Args:
            document_id: Unique document identifier
            filename: Original filename (if None, deletes entire document directory)
            
        Returns:
            True if deletion was successful
        """
        if filename:
            file_path = self._generate_file_path(document_id, filename)
            return await self.backend.delete_file(file_path)
        else:
            # Delete entire document directory
            try:
                # For local storage, we can delete the directory
                if isinstance(self.backend, LocalFileStorage):
                    import shutil
                    doc_dir = self.backend.base_path / document_id
                    if doc_dir.exists():
                        shutil.rmtree(doc_dir)
                        return True
                return False
            except Exception:
                return False
    
    async def document_exists(self, document_id: str, filename: str) -> bool:
        """
        Check if document exists in storage
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            
        Returns:
            True if document exists
        """
        file_path = self._generate_file_path(document_id, filename)
        return await self.backend.file_exists(file_path)
    
    def get_storage_info(self) -> dict:
        """Get information about storage backend"""
        return {
            "backend_type": type(self.backend).__name__,
            "base_path": getattr(self.backend, 'base_path', None)
        }