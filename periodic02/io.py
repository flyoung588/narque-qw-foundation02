"""Content-addressed immutable local evidence. Stdlib, no remote mutations."""
import hashlib
import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def freeze_json(path, value):
    """Atomic no-overwrite creation. Directories may be created; old evidence never rewritten."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, ensure_ascii=False, sort_keys=True,
                          indent=2, allow_nan=False) + '\n').encode('utf-8')
    descriptor = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, 'wb') as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        try:
            dest.unlink()
        except FileNotFoundError:
            pass
        raise
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
