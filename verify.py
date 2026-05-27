"""Server-side verification for rapp-commons-event/1.0 — identical canonicalization
to the browser UI and the Python client, so the cloud host enforces the same rules
no one has to trust it for. (sign everything · be yourself · bounded body · known kind)"""

import base64
import hashlib
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

ALLOWED_KINDS = {"hello", "post", "reply", "topic", "reaction", "walk", "leave"}
MAX_TEXT = 8192
# Only P-256 (ECDSA over SECP256R1) is verifiable below. `alg` is optional for
# back-compat — when absent we assume P-256, the only thing the browser/Python
# client and this host have ever signed with — but if present it must say so.
ALLOWED_ALGS = {"ecdsa-p256", "p-256"}


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _ub64u(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    return base64.b64decode(s + "=" * (-len(s) % 4))


def canonical(obj) -> bytes:
    # recursively key-sorted, compact, UTF-8 — matches JS stableStringify and the Python client
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def event_id(ev: dict) -> str:
    return _b64u(hashlib.sha256(canonical(ev)).digest())[:22]


def verify_event(ev) -> tuple[bool, str]:
    """Returns (ok, reason). The host appends only events that pass."""
    if not isinstance(ev, dict):
        return False, "not an object"
    if ev.get("schema") != "rapp-commons-event/1.0":
        return False, "bad schema"
    for f in ("from", "pub", "sig", "kind", "ts"):
        if f not in ev:
            return False, f"missing {f}"
    if not str(ev["from"]).startswith("rappid:v3:"):
        return False, "from must be a self-generated rappid:v3"
    if ev["kind"] not in ALLOWED_KINDS:
        return False, f"unknown kind {ev['kind']!r}"
    alg = ev.get("alg")
    if alg is not None and str(alg).lower() not in ALLOWED_ALGS:
        return False, f"unsupported alg {alg!r} (only ECDSA P-256)"
    body = ev.get("body")
    text = body.get("text") if isinstance(body, dict) else body
    if isinstance(text, str) and len(text) > MAX_TEXT:
        return False, "body text too long"
    try:
        raw = _ub64u(ev["pub"])
        if "rappid:v3:" + _b64u(hashlib.sha256(raw).digest()) != ev["from"]:
            return False, "fingerprint does not match rappid (be yourself)"
        pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)
        sig = _ub64u(ev["sig"])
        if len(sig) != 64:
            return False, "signature length"
        der = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
        no_sig = {k: v for k, v in ev.items() if k != "sig"}
        pub.verify(der, canonical(no_sig), ec.ECDSA(hashes.SHA256()))
        return True, "ok"
    except Exception:
        return False, "signature invalid"
