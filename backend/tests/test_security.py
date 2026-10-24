from app.core.security import hash_password, verify_password, create_opaque_token

def test_argon2_hashing():
    pwd = "SecretPass123!"
    h = hash_password(pwd)
    assert h != pwd
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPass", h) is False

def test_opaque_token_generation():
    token, token_hash = create_opaque_token()
    assert len(token) >= 32
    assert len(token_hash) == 64
