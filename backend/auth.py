"""
RZWire — password hashing and session cookie helpers.

Closed system: accounts are created via create_account.py, not over HTTP.
"""

import hashlib
import hmac
import os
from http.cookies import SimpleCookie

import database

SESSION_COOKIE_NAME = 'rzwire_session'
PBKDF2_ITERATIONS = 200_000


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return f'{salt.hex()}${digest.hex()}'


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split('$')
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(expected.hex(), digest_hex)


def valid_password(password):
    return isinstance(password, str) and len(password) >= 8


def get_current_user(handler):
    cookie_header = handler.headers.get('Cookie', '')
    cookies = SimpleCookie()
    cookies.load(cookie_header)
    if SESSION_COOKIE_NAME not in cookies:
        return None
    token = cookies[SESSION_COOKIE_NAME].value
    user_id = database.get_user_id_for_session(token)
    if user_id is None:
        return None
    return database.get_user_by_id(user_id)


def get_session_token(handler):
    cookie_header = handler.headers.get('Cookie', '')
    cookies = SimpleCookie()
    cookies.load(cookie_header)
    if SESSION_COOKIE_NAME not in cookies:
        return None
    return cookies[SESSION_COOKIE_NAME].value


def make_session_cookie(token, secure, ttl_days=database.SESSION_TTL_DAYS, remember=True):
    parts = [
        f'{SESSION_COOKIE_NAME}={token}',
        'HttpOnly',
        'Path=/',
        'SameSite=Lax',
    ]
    if remember:
        parts.append(f'Max-Age={ttl_days * 24 * 3600}')
    if secure:
        parts.append('Secure')
    return '; '.join(parts)


def make_clear_cookie(secure):
    parts = [
        f'{SESSION_COOKIE_NAME}=',
        'HttpOnly',
        'Path=/',
        'SameSite=Lax',
        'Max-Age=0',
    ]
    if secure:
        parts.append('Secure')
    return '; '.join(parts)
