"""
modules/historico.py — Gerenciamento do histórico de toner
"""
from database import salvar_historico, buscar_historico, buscar_historico_resumido


def registrar_leitura(impressora_id, percentual, status, tempo_resposta=None):
    """
    Salva uma leitura no histórico.
    Chamado após cada consulta SNMP bem-sucedida.
    """
    if not impressora_id:
        return
    salvar_historico(impressora_id, percentual, status, tempo_resposta)


def obter_historico_card(impressora_id):
    """
    Retorna dados compactos para o sparkline do card.
    Retorna lista de percentuais (últimas 48 leituras).
    """
    leituras = buscar_historico_resumido(impressora_id, limite=48)
    return [l["percentual"] for l in leituras if l["percentual"] is not None]


def obter_historico_completo(impressora_id, dias=30):
    """
    Retorna histórico completo para o gráfico detalhado.
    """
    return buscar_historico(impressora_id, dias=dias, limite=500)


def calcular_previsao_fim(historico):
    """
    Estima em quantos dias o toner vai acabar com base na tendência.
    Usa regressão linear simples sobre os últimos 7 dias de leituras.
    Retorna número de dias ou None se não for possível calcular.
    """
    if len(historico) < 4:
        return None

    # Pega últimas 20 leituras com percentual válido
    leituras = [
        h for h in historico[-20:]
        if h.get("percentual") is not None and h["percentual"] >= 0
    ]
    if len(leituras) < 4:
        return None

    # Converte timestamps para índices numéricos
    from datetime import datetime
    try:
        tempos = []
        valores = []
        for i, l in enumerate(leituras):
            tempos.append(i)
            valores.append(l["percentual"])

        n    = len(tempos)
        sx   = sum(tempos)
        sy   = sum(valores)
        sxy  = sum(t * v for t, v in zip(tempos, valores))
        sx2  = sum(t * t for t in tempos)
        denom = n * sx2 - sx * sx

        if denom == 0:
            return None

        slope = (n * sxy - sx * sy) / denom

        if slope >= 0:
            return None  # Toner não está consumindo

        # Extrapolação: quantos passos até chegar em 5%?
        atual  = valores[-1]
        passos = (5 - atual) / slope  # negativo / negativo = positivo

        if passos <= 0:
            return None

        # Estima intervalo médio entre leituras
        if len(leituras) >= 2:
            dt0 = datetime.fromisoformat(leituras[0]["registrado_em"].replace(" ","T"))
            dt1 = datetime.fromisoformat(leituras[-1]["registrado_em"].replace(" ","T"))
            horas_total = abs((dt1 - dt0).total_seconds()) / 3600
            intervalo_h = horas_total / max(len(leituras) - 1, 1)
        else:
            intervalo_h = 1

        dias_previstos = (passos * intervalo_h) / 24
        return round(dias_previstos)

    except Exception:
        return None
