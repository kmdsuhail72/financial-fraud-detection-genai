"""
FinGuard AI — Phase 26: Cryptographic Document Integrity & Hashing
"""
import hashlib
from typing import Union
from document_verification.models import DocumentFormat


def compute_sha256(content: Union[str, bytes]) -> str:
    """Computes standard SHA-256 hexadecimal digest for raw or decoded content."""
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content
    return hashlib.sha256(content_bytes).hexdigest()


def get_mime_type(file_format: DocumentFormat) -> str:
    """Returns canonical MIME type for supported document formats."""
    mapping = {
        DocumentFormat.PDF: "application/pdf",
        DocumentFormat.JPEG: "image/jpeg",
        DocumentFormat.PNG: "image/png"
    }
    return mapping.get(file_format, "application/octet-stream")


def verify_content_integrity(recorded_sha256: str, current_content: Union[str, bytes]) -> bool:
    """
    Returns True if current content SHA-256 matches the recorded digest;
    returns False if modified/tampered.
    """
    current_hash = compute_sha256(current_content)
    return current_hash.lower() == recorded_sha256.lower()

