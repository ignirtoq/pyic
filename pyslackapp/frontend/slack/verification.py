import hmac


__all__ = [
    'SignatureVerificationError',
    'verify_signature',
]


HEADER_SIGNATURE = 'X-Slack-Signature'
HEADER_TIMESTAMP = 'X-Slack-Request-Timestamp'
SLACK_VERSION = 'v0'
DELIMITER = ':'


class SignatureVerificationError(ValueError):
    """Provided message signature did not match computed message signature."""


def verify_signature(private_key, headers, body):
    provided_sig = headers.get(HEADER_SIGNATURE, '')
    timestamp = f'{headers.get(HEADER_TIMESTAMP, "")}'
    body = body.decode()
    computed_sig = _data_to_signature(private_key, timestamp, body)
    if not provided_sig.lower() == computed_sig.lower():
        raise SignatureVerificationError(
            f'provided signature\n{provided_sig}\ndoes not match expected\n'
            f'{computed_sig}')


def _data_to_signature(private_key, timestamp, body):
    v, d = SLACK_VERSION, DELIMITER
    data = f'{v}{d}{timestamp}{d}{body}'
    return f'v0={_compute_hash_sha256(private_key, data)}'


def _compute_hash_sha256(key, msg):
    bkey = key if isinstance(key, bytes) else key.encode()
    msg = msg if isinstance(msg, bytes) else msg.encode()
    return hmac.new(bkey, msg, 'sha256').hexdigest()

