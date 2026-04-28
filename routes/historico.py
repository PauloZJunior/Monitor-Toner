"""
routes/historico.py — Endpoints de histórico de toner
Blueprint: /historico
"""
from flask import Blueprint, jsonify, request
from database import buscar_por_id
from modules.historico import obter_historico_completo, calcular_previsao_fim

historico_bp = Blueprint("historico", __name__, url_prefix="/historico")


@historico_bp.route("/impressoras/<int:id_>")
def historico_impressora(id_):
    imp = buscar_por_id(id_)
    if not imp:
        return jsonify({"erro": "Impressora não encontrada"}), 404

    try:
        dias = max(1, min(int(request.args.get("dias", 30)), 90))
    except (ValueError, TypeError):
        dias = 30

    leituras = obter_historico_completo(id_, dias=dias)
    previsao = calcular_previsao_fim(leituras)

    return jsonify({
        "impressora": {
            "id":     imp["id"],
            "nome":   imp["nome"],
            "modelo": imp["modelo"],
            "setor":  imp["setor"],
        },
        "leituras":         leituras,
        "total":            len(leituras),
        "dias_solicitados": dias,
        "previsao_dias":    previsao,
    })
