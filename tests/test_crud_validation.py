"""
Testes de routes/crud.py — validação de IP e SNMP community string.

Essas duas funções são a linha de defesa contra dados inválidos/maliciosos
no cadastro de impressoras (ex: community usada em algum lugar sem
parametrização correta, ou IPs especiais que não fazem sentido numa
impressora de rede). Vale garantir que continuam rejeitando o que devem
rejeitar, mesmo depois de refatorações futuras.
"""
from routes.crud import _validar_ip, _validar_community


# ─── _validar_ip ─────────────────────────────────────────────────────────

def test_ip_valido_comum():
    assert _validar_ip("192.168.1.100") is True
    assert _validar_ip("172.20.130.68") is True


def test_ip_loopback_e_rejeitado():
    assert _validar_ip("127.0.0.1") is False


def test_ip_multicast_e_rejeitado():
    assert _validar_ip("224.0.0.1") is False


def test_ip_nao_especificado_e_rejeitado():
    assert _validar_ip("0.0.0.0") is False


def test_ip_malformado_e_rejeitado():
    assert _validar_ip("999.999.999.999") is False
    assert _validar_ip("nao-e-um-ip") is False
    assert _validar_ip("") is False
    assert _validar_ip("192.168.1") is False


# ─── _validar_community ──────────────────────────────────────────────────

def test_community_vazia_e_permitida_default_public():
    assert _validar_community("") is True
    assert _validar_community(None) is True


def test_community_alfanumerica_e_permitida():
    assert _validar_community("public") is True
    assert _validar_community("Setor_TI-01.rede") is True


def test_community_com_caracteres_perigosos_e_rejeitada():
    # Tentativas de injeção/escape não devem passar
    assert _validar_community("public' OR '1'='1") is False
    assert _validar_community("public; rm -rf /") is False
    assert _validar_community("<script>alert(1)</script>") is False


def test_community_muito_longa_e_rejeitada():
    assert _validar_community("a" * 33) is False
    assert _validar_community("a" * 32) is True
