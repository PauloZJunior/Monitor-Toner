"""
routes/crud.py — Endpoints de gerenciamento de impressoras (CRUD)
Blueprint: /gerenciar

GET  /gerenciar/impressoras         → lista todas (público)
GET  /gerenciar/impressoras/<id>    → busca uma (público)
POST /gerenciar/impressoras         → cria (requer autenticação)
PUT  /gerenciar/impressoras/<id>    → atualiza (requer autenticação)
DELETE /gerenciar/impressoras/<id>  → exclui (requer autenticação)
"""
import re
import ipaddress
import sqlite3
from flask import Blueprint, jsonify, request
from database import (
    listar_impressoras, buscar_por_id, buscar_por_ip,
    criar_impressora, atualizar_impressora, excluir_impressora,
)
from routes.auth import requer_autenticacao

crud_bp = Blueprint("crud", __name__, url_prefix="/gerenciar")

CAMPOS_OBRIGATORIOS = ["nome", "ip"]
CAMPOS_VALIDOS      = ["nome", "ip", "modelo", "tipo", "setor", "empresa",
                       "serial", "mac", "community", "ativo"]


def _validar_ip(ip_str: str) -> bool:
    """Valida formato de IPv4 usando ipaddress built-in"""
    try:
        addr = ipaddress.IPv4Address(ip_str)
        # Rejeita broadcast, network, multicast
        if addr.is_reserved or addr.is_loopback or addr.is_multicast or addr.is_unspecified:
            return False
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def _validar_community(community: str) -> bool:
    """Valida SNMP community string — rejeita caracteres especiais que podem ser SQL injection"""
    if not community:
        return True  # "public" é padrão se vazio
    # Apenas alphanumeric, _, -, . permitidos
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]{1,32}$', community))


def _validar_dados(dados, exigir_obrigatorios=True):
    """Valida os dados recebidos. Retorna (dados_limpos, erro_str | None)."""
    erros = []

    if exigir_obrigatorios:
        for campo in CAMPOS_OBRIGATORIOS:
            if not dados.get(campo, "").strip():
                erros.append(f"Campo obrigatório: {campo}")

    # Validação de IP
    ip = dados.get("ip", "").strip()
    if ip:
        if not _validar_ip(ip):
            erros.append("IP inválido — use formato válido como 192.168.1.100")

    # Validação de SNMP Community (proteção contra SQL injection)
    community = dados.get("community", "public").strip()
    if community and not _validar_community(community):
        erros.append("Community SNMP inválida — use apenas letras, números, _, -, .")

    if erros:
        return None, "; ".join(erros)

    return {k: dados.get(k, "") for k in CAMPOS_VALIDOS
            if k in dados or k in CAMPOS_OBRIGATORIOS}, None


# ─── LEITURA (pública) ───────────────────────────────
@crud_bp.route("/impressoras")
def listar():
    """Retorna todas as impressoras para o gerenciador (incluindo inativas)."""
    impressoras = listar_impressoras(apenas_ativas=False)
    return jsonify({"impressoras": impressoras, "total": len(impressoras)})


@crud_bp.route("/impressoras/<int:id_>")
def buscar(id_):
    """Retorna uma impressora pelo ID."""
    imp = buscar_por_id(id_)
    if not imp:
        return jsonify({"erro": "Impressora não encontrada"}), 404
    return jsonify(imp)


# ─── ESCRITA (requer autenticação) ───────────────────
@crud_bp.route("/impressoras", methods=["POST"])
@requer_autenticacao
def criar():
    """Cadastra nova impressora."""
    dados = request.get_json(silent=True) or {}
    dados_limpos, erro = _validar_dados(dados)

    if erro:
        return jsonify({"erro": erro}), 400

    if buscar_por_ip(dados_limpos["ip"]):
        return jsonify({"erro": f"Já existe uma impressora com o IP {dados_limpos['ip']}"}), 409

    try:
        novo_id = criar_impressora(dados_limpos)
        return jsonify({
            "sucesso": True,
            "id": novo_id,
            "mensagem": "Impressora cadastrada com sucesso"
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"erro": "IP já cadastrado"}), 409
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@crud_bp.route("/impressoras/<int:id_>", methods=["PUT"])
@requer_autenticacao
def atualizar(id_):
    """Atualiza dados de uma impressora."""
    if not buscar_por_id(id_):
        return jsonify({"erro": "Impressora não encontrada"}), 404

    dados = request.get_json(silent=True) or {}
    dados_limpos, erro = _validar_dados(dados)

    if erro:
        return jsonify({"erro": erro}), 400

    # Verifica se o novo IP já existe em outra impressora
    ip_existente = buscar_por_ip(dados_limpos.get("ip", ""))
    if ip_existente and ip_existente["id"] != id_:
        return jsonify({
            "erro": f"O IP {dados_limpos['ip']} já está em uso por outra impressora"
        }), 409

    try:
        dados_limpos["ativo"] = dados.get("ativo", 1)
        atualizar_impressora(id_, dados_limpos)
        return jsonify({"sucesso": True, "mensagem": "Impressora atualizada com sucesso"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@crud_bp.route("/impressoras/<int:id_>", methods=["DELETE"])
@requer_autenticacao
def excluir(id_):
    """Remove uma impressora permanentemente."""
    if not buscar_por_id(id_):
        return jsonify({"erro": "Impressora não encontrada"}), 404

    try:
        excluir_impressora(id_)
        return jsonify({"sucesso": True, "mensagem": "Impressora removida com sucesso"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
