"""
Testes de modules/toner.py — detecção de fabricante.

É uma função pequena e pura, mas central: se ela classificar errado, a
impressora inteira cai na estratégia de leitura de toner errada (ex: tenta
ler uma Brother pela Printer-MIB padrão da Samsung) e o painel mostra "N/D"
ou um valor incorreto sem nenhum erro visível.
"""
from modules.toner import detectar_fabricante


def test_detecta_brother():
    assert detectar_fabricante("Brother HL-2140") == "brother"
    assert detectar_fabricante("brother dcp-7065dn") == "brother"


def test_detecta_ricoh():
    assert detectar_fabricante("Ricoh SP 3710SF") == "ricoh"


def test_detecta_epson():
    assert detectar_fabricante("EPSON WF-L6490") == "epson"


def test_deteccao_e_case_insensitive():
    assert detectar_fabricante("RICOH sp c261sfnw") == "ricoh"


def test_modelo_desconhecido_cai_no_padrao():
    # Samsung e qualquer modelo genérico caem no fluxo padrão (Printer-MIB)
    assert detectar_fabricante("Samsung M4070FR") == "padrao"
    assert detectar_fabricante("HP LaserJet Pro") == "padrao"


def test_modelo_vazio_ou_none_nao_quebra():
    assert detectar_fabricante("") == "padrao"
    assert detectar_fabricante(None) == "padrao"


def test_substring_no_meio_do_texto_tambem_e_detectada():
    # A função usa "in", não igualdade exata — confirma que funciona mesmo
    # com texto livre ao redor do nome do fabricante.
    assert detectar_fabricante("Impressora Epson multifuncional, setor financeiro") == "epson"
