from cryptography.hazmat.primitives.asymmetric import ed25519

from qqbotsdk.crypto import build_seed, sign_msg, verify_sig


def test_build_seed_pads_to_32_bytes():
    assert len(build_seed("abc")) == 32
    assert len(build_seed("x" * 32)) == 32
    assert len(build_seed("x" * 40)) == 32
    # 同一 secret 展开结果稳定
    assert build_seed("abc") == build_seed("abc")


def test_sign_and_verify_roundtrip():
    secret = "test-secret"
    timestamp = "1726000000"
    plain_token = "plain_token"
    sig = sign_msg(secret, timestamp + plain_token)
    # sign_msg 产出 hex 编码的 Ed25519 签名（64 字节 = 128 hex 字符）
    assert len(sig) == 128
    assert verify_sig(secret, timestamp, sig, plain_token.encode())


def test_verify_sig_accepts_valid_signature():
    secret = "test-secret"
    timestamp = "1726000000"
    body = b'{"plain_token":"abc"}'
    # 签名内容 = timestamp + body
    key = ed25519.Ed25519PrivateKey.from_private_bytes(build_seed(secret))
    signature = key.sign(timestamp.encode() + body).hex()
    assert verify_sig(secret, timestamp, signature, body)


def test_verify_sig_rejects_tampered_body():
    secret = "test-secret"
    timestamp = "1726000000"
    body = b'{"plain_token":"abc"}'
    sig = sign_msg(secret, timestamp + body.decode())
    assert not verify_sig(secret, timestamp, sig, b'{"plain_token":"xyz"}')


def test_verify_sig_rejects_bad_hex():
    assert not verify_sig("secret", "123", "not-hex", b"body")
