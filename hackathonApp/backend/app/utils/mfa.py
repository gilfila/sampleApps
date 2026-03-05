"""MFA utility functions for TOTP, backup codes, encryption, and device trust."""

import os
import io
import base64
import hashlib
import secrets
import logging
from datetime import datetime, timedelta

import bcrypt
import jwt
import pyotp
import qrcode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TOTP
# ---------------------------------------------------------------------------

def generate_totp_secret():
    """Generate a new random TOTP secret using pyotp."""
    return pyotp.random_base32()


def generate_qr_code(secret, account, issuer='HackathonApp'):
    """Generate a QR code for TOTP enrollment.

    Returns a data-URI string (``data:image/png;base64,...``).
    """
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=account,
        issuer_name=issuer
    )
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{b64}'


def verify_totp_code(secret, code):
    """Verify a TOTP code with +/- 1 step tolerance (30 s each side)."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ---------------------------------------------------------------------------
# AES-256-GCM encryption for TOTP secrets at rest
# ---------------------------------------------------------------------------

def _get_encryption_key():
    """Return the 32-byte AES key from config."""
    from config import Config
    raw = Config.MFA_ENCRYPTION_KEY
    if not raw:
        raise RuntimeError("MFA_ENCRYPTION_KEY is not configured")
    # Accept either raw 32 bytes (hex-encoded 64 chars) or base64
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        key = base64.b64decode(raw)
    if len(key) != 32:
        raise RuntimeError("MFA_ENCRYPTION_KEY must be 32 bytes (256 bits)")
    return key


def encrypt_secret(plaintext):
    """Encrypt a TOTP secret with AES-256-GCM.

    Returns (ciphertext_bytes, nonce_bytes).
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_encryption_key()
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return ciphertext, nonce


def decrypt_secret(ciphertext, nonce):
    """Decrypt a TOTP secret encrypted with AES-256-GCM."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')


# ---------------------------------------------------------------------------
# MFA token (short-lived JWT issued after password-only verification)
# ---------------------------------------------------------------------------

def _get_jwt_secret():
    from config import Config
    secret = Config.MFA_JWT_SECRET or Config.SECRET_KEY
    if not secret:
        raise RuntimeError("No JWT secret configured for MFA tokens")
    return secret


def generate_mfa_token(user_id):
    """Create a 5-minute JWT for the MFA verification step."""
    payload = {
        'user_id': user_id,
        'purpose': 'mfa_verify',
        'exp': datetime.utcnow() + timedelta(minutes=5),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm='HS256')


def verify_mfa_token(token):
    """Validate an MFA token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=['HS256'])
        if payload.get('purpose') != 'mfa_verify':
            return None
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        logger.debug("MFA token expired")
        return None
    except jwt.InvalidTokenError:
        logger.debug("Invalid MFA token")
        return None


# ---------------------------------------------------------------------------
# Backup codes
# ---------------------------------------------------------------------------

def generate_backup_codes(count=8, length=8):
    """Generate a list of random alphanumeric backup codes."""
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return [''.join(secrets.choice(alphabet) for _ in range(length)) for _ in range(count)]


def hash_backup_code(code):
    """Hash a backup code with bcrypt."""
    return bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_backup_code(code, hashed):
    """Verify a backup code against its bcrypt hash."""
    return bcrypt.checkpw(code.upper().encode('utf-8'), hashed.encode('utf-8'))


# ---------------------------------------------------------------------------
# Trusted-device tokens
# ---------------------------------------------------------------------------

def generate_device_token():
    """Generate a random 64-character hex string for trusted device cookies."""
    return secrets.token_hex(32)


def hash_device_token(token):
    """SHA-256 hash of a device token (stored in DB)."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
