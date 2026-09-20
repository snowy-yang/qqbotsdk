"""Ed25519 签名工具：QQ 开放平台 webhook 验签/验证应答所用。

seed 派生规则（官方约定）：AppSecret 的 utf8 字节反复倍增补足 32 字节。
"""

from functools import cache

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

_ED25519_SEED_SIZE = 32


def build_seed(secret: str) -> bytes:
    seed = secret.encode("utf-8")
    while len(seed) < _ED25519_SEED_SIZE:
        seed *= 2
    return seed[:_ED25519_SEED_SIZE]


@cache
def _private_key(secret: str) -> ed25519.Ed25519PrivateKey:
    """AppSecret → Ed25519 私钥。

    派生一次约 40µs（每个 webhook 请求都要验签），而进程内 secret 是固定的，
    按 secret 缓存即可把这一步省掉。公钥派生只差 3µs，不值得再缓存一层。
    """
    return ed25519.Ed25519PrivateKey.from_private_bytes(build_seed(secret))


def sign_msg(secret: str, msg: str) -> str:
    return _private_key(secret).sign(msg.encode("utf-8")).hex()


def verify_sig(secret: str, timestamp: str, signature: str, body: bytes) -> bool:
    try:
        sig = bytes.fromhex(signature)
        _private_key(secret).public_key().verify(sig, timestamp.encode("utf-8") + body)
        return True
    except (InvalidSignature, ValueError):
        return False
