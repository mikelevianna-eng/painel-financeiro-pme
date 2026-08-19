"""Análise financeira do escritório de contabilidade."""

import pandas as pd

HOJE = pd.Timestamp("2025-12-31")


def carregar():
    cl = pd.read_csv("clientes.csv", parse_dates=["data_inicio_contrato"])
    rc = pd.read_csv("contas_receber.csv",
                     parse_dates=["data_vencimento", "data_pagamento"])
    pg = pd.read_csv("contas_pagar.csv", parse_dates=["data_vencimento"])
    return cl, rc, pg


# ---------------------------------------------------------------------
# DRE mensal
# ---------------------------------------------------------------------

def dre_mensal(rc, pg):
    """
    DRE por competência, ou seja, pelo mês a que a receita e a despesa
    se referem, não pela data em que o dinheiro efetivamente mudou de
    mão. É o regime que mostra se o negócio é lucrativo.
    """
    receita = rc.groupby("competencia")["valor"].sum().rename("receita")
    despesa = pg.groupby("competencia")["valor"].sum().rename("despesa")

    dre = pd.concat([receita, despesa], axis=1).fillna(0).reset_index()
    dre = dre.rename(columns={"index": "competencia"})
    dre["resultado"] = dre["receita"] - dre["despesa"]
    dre["margem_pct"] = (dre["resultado"] / dre["receita"] * 100).round(1)
    return dre.sort_values("competencia").reset_index(drop=True)


# ---------------------------------------------------------------------
# Regime de caixa: quando o dinheiro entrou de verdade
# ---------------------------------------------------------------------

def caixa_mensal(rc, pg):
    """
    Fluxo de caixa por regime de caixa, pela data em que o pagamento
    aconteceu, não pela competência. É o que explica por que o mês
    fecha no vermelho mesmo com contrato assinado: o dinheiro daquele
    mês entrou atrasado, no mês seguinte.
    """
    pago = rc[rc["status"] == "Pago"].copy()
    pago["mes_recebimento"] = pago["data_pagamento"].dt.to_period("M").astype(str)
    entradas = pago.groupby("mes_recebimento")["valor"].sum().rename("entradas")

    pg = pg.copy()
    pg["mes_pagamento"] = pg["data_vencimento"].dt.to_period("M").astype(str)
    saidas = pg.groupby("mes_pagamento")["valor"].sum().rename("saidas")

    caixa = pd.concat([entradas, saidas], axis=1).fillna(0).reset_index()
    caixa = caixa.rename(columns={"index": "mes"})
    caixa["saldo_mes"] = caixa["entradas"] - caixa["saidas"]
    caixa["saldo_acumulado"] = caixa["saldo_mes"].cumsum()
    return caixa.sort_values("mes").reset_index(drop=True)


# ---------------------------------------------------------------------
# Inadimplência por cliente
# ---------------------------------------------------------------------

def atraso_medio(rc):
    """Dias entre vencimento e pagamento, só para títulos já pagos."""
    pago = rc[rc["status"] == "Pago"].copy()
    pago["dias_atraso"] = (pago["data_pagamento"] - pago["data_vencimento"]).dt.days
    return pago


def inadimplencia_por_cliente(rc, clientes):
    pago = atraso_medio(rc)

    r = pago.groupby("id_cliente").agg(
        titulos_pagos=("id_titulo", "count"),
        atraso_medio=("dias_atraso", "mean"),
        atraso_maximo=("dias_atraso", "max"),
        pontual_pct=("dias_atraso", lambda s: (s <= 5).mean() * 100),
    ).reset_index()

    aberto = rc[rc["status"] == "Em aberto"].groupby("id_cliente").agg(
        titulos_em_aberto=("id_titulo", "count"),
        valor_em_aberto=("valor", "sum"),
    ).reset_index()

    r = r.merge(aberto, on="id_cliente", how="left").fillna({
        "titulos_em_aberto": 0, "valor_em_aberto": 0})
    r = r.merge(clientes[["id_cliente", "razao_social", "segmento",
                          "plano", "honorario_mensal"]], on="id_cliente")

    r["risco"] = pd.cut(
        r["atraso_medio"], [-1, 5, 15, 30, 9999],
        labels=["Pontual", "Atenção", "Risco", "Alto risco"])

    return r.sort_values("atraso_medio", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------
# Projeção de recebíveis
# ---------------------------------------------------------------------

def projetar_recebimento(rc, inadimplencia, dias=90):
    """
    Estima quando os títulos em aberto vão entrar, aplicando a cada
    cliente o atraso médio dele mesmo, e não uma média geral. É o que
    transforma a data de vencimento contratual na data provável de
    entrada no caixa.
    """
    aberto = rc[rc["status"] == "Em aberto"].merge(
        inadimplencia[["id_cliente", "atraso_medio"]], on="id_cliente", how="left")
    aberto["atraso_medio"] = aberto["atraso_medio"].fillna(
        inadimplencia["atraso_medio"].median())

    aberto["previsao_recebimento"] = aberto["data_vencimento"] + \
        pd.to_timedelta(aberto["atraso_medio"].round(), unit="D")

    horizonte = HOJE + pd.Timedelta(days=dias)
    janela = aberto[aberto["previsao_recebimento"] <= horizonte].copy()
    janela["semana"] = janela["previsao_recebimento"].dt.to_period("W").astype(str)

    faixas = [30, 60, 90]
    resumo = {}
    for f in faixas:
        limite = HOJE + pd.Timedelta(days=f)
        resumo[f"ate_{f}_dias"] = round(
            aberto[aberto["previsao_recebimento"] <= limite]["valor"].sum(), 2)

    return aberto.sort_values("previsao_recebimento"), resumo


# ---------------------------------------------------------------------
# Ponto de equilíbrio
# ---------------------------------------------------------------------

def ponto_de_equilibrio(dre, despesas_variaveis_pct=0.06):
    """
    Faturamento necessário para cobrir o custo fixo, dado que parte da
    despesa cresce junto com a receita.

    O custo fixo é isolado subtraindo da despesa média a parcela que
    varia com o faturamento. Ponto de equilíbrio = custo fixo dividido
    por um menos o percentual variável, porque cada real faturado
    também gera despesa variável e só a diferença cobre o fixo.

    O percentual variável não é calculado dos dados, é assumido pela
    premissa de geração da base, e num caso real precisa ser levantado
    com o cliente a partir da composição real dos custos.
    """
    receita_media = dre["receita"].mean()
    despesa_media = dre["despesa"].mean()

    custo_variavel_medio = receita_media * despesas_variaveis_pct
    custo_fixo_medio = despesa_media - custo_variavel_medio

    equilibrio = custo_fixo_medio / (1 - despesas_variaveis_pct)

    return {
        "receita_media_mensal": round(receita_media, 2),
        "despesa_media_mensal": round(despesa_media, 2),
        "custo_fixo_estimado": round(custo_fixo_medio, 2),
        "custo_variavel_estimado": round(custo_variavel_medio, 2),
        "ponto_de_equilibrio": round(equilibrio, 2),
        "folga_sobre_equilibrio_pct": round(receita_media / equilibrio * 100 - 100, 1),
    }


if __name__ == "__main__":
    pd.set_option("display.width", 200)

    cl, rc, pg = carregar()
    dre = dre_mensal(rc, pg)
    caixa = caixa_mensal(rc, pg)
    inad = inadimplencia_por_cliente(rc, cl)
    projecao, resumo_proj = projetar_recebimento(rc, inad)
    pe = ponto_de_equilibrio(dre)

    print("=" * 78)
    print("DRE MENSAL (últimos 6 meses)")
    print(dre.tail(6).round(1).to_string(index=False))

    print()
    print("=" * 78)
    print("CAIXA (últimos 6 meses)")
    print(caixa.tail(6).round(1).to_string(index=False))

    print()
    print("=" * 78)
    print("RISCO POR CLIENTE")
    print(inad["risco"].value_counts().to_string())
    print()
    print(inad.head(8)[["razao_social", "plano", "atraso_medio", "atraso_maximo",
                        "titulos_em_aberto", "valor_em_aberto", "risco"]]
          .round(1).to_string(index=False))

    print()
    print("=" * 78)
    print("PROJEÇÃO DE RECEBÍVEIS")
    print(resumo_proj)

    print()
    print("=" * 78)
    print("PONTO DE EQUILÍBRIO")
    print(pe)
