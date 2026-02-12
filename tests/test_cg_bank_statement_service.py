from app.utils.bank_parser import _env_default_passwords


def test_env_default_passwords_parse(monkeypatch):
    monkeypatch.setenv('BANK_STATEMENT_PASSWORD', '15041990, 12091988,,28071997 ')
    assert _env_default_passwords() == ['15041990', '12091988', '28071997']


def test_env_default_passwords_empty(monkeypatch):
    monkeypatch.delenv('BANK_STATEMENT_PASSWORD', raising=False)
    assert _env_default_passwords() == []
