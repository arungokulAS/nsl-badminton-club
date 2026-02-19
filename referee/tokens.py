import secrets
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache

TOKEN_EXPIRY_MINUTES = getattr(settings, 'REFEREE_TOKEN_EXPIRY', 180)

def generate_referee_token(court_id, round_id):
    token = secrets.token_urlsafe(24)
    key = f"referee_token:{token}"
    expiry = datetime.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
    cache.set(key, {'court_id': court_id, 'round_id': round_id, 'expires': expiry}, timeout=TOKEN_EXPIRY_MINUTES*60)
    return token

def validate_referee_token(token):
    key = f"referee_token:{token}"
    data = cache.get(key)
    if not data:
        return None
    if data['expires'] < datetime.now():
        cache.delete(key)
        return None
    return data
