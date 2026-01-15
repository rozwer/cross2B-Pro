"""Encryption service for API keys and sensitive data.

Uses AES-256-GCM for authenticated encryption.
SECURITY: API keys must NEVER appear in logs.
"""

import base64
import logging
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# Environment variable for encryption key
ENCRYPTION_KEY_ENV = "SETTINGS_ENCRYPTION_KEY"

# AES-256 key size in bytes
KEY_SIZE = 32

# GCM nonce size in bytes (96 bits recommended by NIST)
NONCE_SIZE = 12


class EncryptionError(Exception):
    """Encryption/decryption error."""

    pass


def _get_encryption_key() -> bytes:
    """Get or generate the encryption key.

    Returns:
        32-byte encryption key

    Raises:
        EncryptionError: If key is invalid or not set
    """
    key_b64 = os.getenv(ENCRYPTION_KEY_ENV)

    if not key_b64:
        raise EncryptionError(
            f"Encryption key not set. Please set {ENCRYPTION_KEY_ENV} environment variable. "
            f'Generate one with: python -c "import secrets; import base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"'
        )

    try:
        key = base64.b64decode(key_b64)
        if len(key) != KEY_SIZE:
            raise EncryptionError(f"Invalid encryption key size: expected {KEY_SIZE} bytes, got {len(key)}")
        return key
    except Exception as e:
        raise EncryptionError(f"Invalid encryption key format: {e}") from e


def encrypt(plaintext: str) -> str:
    """Encrypt a string using AES-256-GCM.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded encrypted string (nonce + ciphertext)

    Raises:
        EncryptionError: If encryption fails
    """
    if not plaintext:
        return ""

    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)

        # Generate random nonce
        nonce = secrets.token_bytes(NONCE_SIZE)

        # Encrypt (GCM provides authentication)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        # Combine nonce + ciphertext and encode
        encrypted = base64.b64encode(nonce + ciphertext).decode("utf-8")
        return encrypted
    except EncryptionError:
        raise
    except Exception as e:
        logger.error("Encryption failed")
        raise EncryptionError("Encryption failed") from e


def decrypt(encrypted: str) -> str:
    """Decrypt a string encrypted with AES-256-GCM.

    Args:
        encrypted: Base64-encoded encrypted string (nonce + ciphertext)

    Returns:
        Decrypted plaintext string

    Raises:
        EncryptionError: If decryption fails
    """
    if not encrypted:
        return ""

    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)

        # Decode and split nonce + ciphertext
        data = base64.b64decode(encrypted)
        if len(data) < NONCE_SIZE:
            raise EncryptionError("Invalid encrypted data: too short")

        nonce = data[:NONCE_SIZE]
        ciphertext = data[NONCE_SIZE:]

        # Decrypt
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except EncryptionError:
        raise
    except Exception as e:
        logger.error("Decryption failed")
        raise EncryptionError("Decryption failed") from e


def mask_api_key(api_key: str, service: str = "") -> str:
    """Mask an API key for display.

    Different masking strategies for different services:
    - GitHub: Show only first 4 chars (ghp_****) due to exposure risk
    - Others: Show last 4 chars (****xyz)

    Args:
        api_key: The API key to mask
        service: The service name (github, gemini, openai, etc.)

    Returns:
        Masked API key string
    """
    if not api_key:
        return ""

    if len(api_key) <= 8:
        return "*" * len(api_key)

    # GitHub tokens need special handling - show only prefix
    if service.lower() == "github":
        return api_key[:4] + "*" * (len(api_key) - 4)

    # For other services, show last 4 chars
    return "*" * (len(api_key) - 4) + api_key[-4:]


def generate_encryption_key() -> str:
    """Generate a new encryption key for initial setup.

    Returns:
        Base64-encoded 32-byte key
    """
    key = secrets.token_bytes(KEY_SIZE)
    return base64.b64encode(key).decode("utf-8")
