import secrets
from django.core.cache import cache

TOKEN_CACHE_TIMEOUT = 60 * 60 * 24 * 365 * 5

def generate_referee_token(court_id, round_id):
    token = secrets.token_urlsafe(24)
    key = f"referee_token:{token}"
    cache.set(key, {'court_id': court_id, 'round_id': round_id}, timeout=TOKEN_CACHE_TIMEOUT)
    return token

def validate_referee_token(token):
    key = f"referee_token:{token}"
    return cache.get(key)
