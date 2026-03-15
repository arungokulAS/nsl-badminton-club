from django.core import signing

def generate_referee_token(court_id, round_id):
    payload = {'court_id': str(court_id), 'round_id': str(round_id)}
    return signing.dumps(payload, salt='referee-token')

def validate_referee_token(token):
    try:
        return signing.loads(token, salt='referee-token')
    except signing.BadSignature:
        return None
