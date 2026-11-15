from get_env import (
    Configuration,
    conf_from_exist_file,
    derive_eddsa_public_key,
    generate_eddsa_private_key,
    generate_login,
    generate_password,
    main,
)


def test_generate_login():
    login1 = generate_login()
    login2 = generate_login()
    assert login1.startswith("shopper_")
    assert login2.startswith("shopper_")
    assert login1 != login2


def test_generate_password():
    pwd1 = generate_password(16)
    pwd2 = generate_password(16)
    assert len(pwd1) >= 16
    assert len(pwd2) >= 16
    assert pwd1 != pwd2


def test_eddsa_key_generation_and_derivation():
    priv = generate_eddsa_private_key()
    pub = derive_eddsa_public_key(priv)
    assert len(priv) == 64
    assert len(pub) == 64
    # Re-deriving from same private key produces same public key
    assert derive_eddsa_public_key(priv) == pub


def test_get_env_script_auto_generation(tmp_path, monkeypatch):
    test_conf = Configuration()
    test_conf.THIS_DIR = tmp_path
    test_conf.BACKUP_DIR = tmp_path / "backups"
    test_conf.FILENAME = ".env.test"

    monkeypatch.setattr("get_env.conf", test_conf)

    main(["--auto"])

    env_file = tmp_path / ".env.test"
    assert env_file.exists()

    parsed = conf_from_exist_file(env_file)
    assert "POSTGRES_USER" in parsed
    assert "POSTGRES_PASSWORD" in parsed
    assert "POSTGRES_DB" in parsed
    assert "DB_URL" in parsed
    assert "JWT_ALGORITHM" in parsed
    assert "JWT_PRIVATE_KEY" in parsed
    assert "JWT_PUBLIC_KEY" in parsed
    assert "PEPPER" in parsed
    assert "REDIS_URL" in parsed
    assert parsed["JWT_ALGORITHM"] == "EdDSA"
    assert parsed["POSTGRES_USER"].startswith("shopper_")
    assert parsed["POSTGRES_USER"] in parsed["DB_URL"]
