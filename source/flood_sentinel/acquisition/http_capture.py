"""Bounded immutable HTTP capture. Receipt time is not historical publication time."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid


def capture(url: str, store: Path, *, max_bytes: int = 32_000_000) -> dict:
    """Save exact response entity bytes and failures, including HTTP error bodies.

    No credentials are accepted in URLs. TLS uses the interpreter's default trust.
    This local manifest records transport evidence, not independent authentication.
    """
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.username or parts.password:
        raise ValueError('HTTPS URL without credentials required')
    if any(x in parts.query.lower() for x in ('api_key', 'token', 'password', 'secret')):
        raise ValueError('Credential-bearing URLs are not captured')
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    rec = dict(request_url=url, started_at=datetime.now(timezone.utc).isoformat(),
               transport='https', status=None, headers={}, error=None, raw_sha256=None)
    try:
        request = Request(url, headers={'Accept':'application/json', 'Accept-Encoding':'identity',
                                       'User-Agent':'FloodSentinel-source-feasibility/0.1'})
        try:
            response = urlopen(request, timeout=45)
        except HTTPError as exc:
            response = exc
        with response:
            rec.update(status=response.code, response_url=response.geturl(),
                       headers={k:v for k,v in response.headers.items()
                                if k.lower() not in {'set-cookie', 'authorization'}})
            raw = response.read(max_bytes+1)
            if len(raw) > max_bytes:
                raise ValueError('Response exceeds declared capture bound; incomplete, not accepted')
            digest = hashlib.sha256(raw).hexdigest()
            target = store / (digest+'.body')
            if target.exists() and target.read_bytes() != raw:
                raise ValueError('Content address collision')
            if not target.exists():
                target.write_bytes(raw)
            rec.update(raw_sha256=digest, byte_length=len(raw), raw_path=target.name)
            if response.code != 200:
                rec['error'] = 'HTTP '+str(response.code)
    except Exception as exc:
        rec['error'] = type(exc).__name__+': '+str(exc)
    rec['received_at'] = datetime.now(timezone.utc).isoformat()
    (store / (str(uuid.uuid4())+'.receipt.json')).write_text(json.dumps(rec,indent=2)+'\n')
    return rec
