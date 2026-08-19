"""Exporta as tabelas financeiras para o Google Sheets, fonte do painel."""

import pandas as pd


def _autenticar():
    try:
        from google.colab import auth
        from google.auth import default
        import gspread
    except ImportError as erro:
        raise RuntimeError(
            "Este módulo foi feito para rodar no Google Colab."
        ) from erro

    auth.authenticate_user()
    credenciais, _ = default()
    return gspread.authorize(credenciais)


def _preparar(df):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_period_dtype(df[c]):
            df[c] = df[c].astype(str)
        elif df[c].dtype.name in ("category", "object"):
            df[c] = df[c].astype(str)
    return df.where(pd.notna(df), "")


def _gravar_aba(planilha, nome, df):
    df = _preparar(df)
    try:
        aba = planilha.worksheet(nome)
        aba.clear()
    except Exception:
        aba = planilha.add_worksheet(
            title=nome, rows=max(len(df) + 10, 100), cols=max(len(df.columns) + 2, 20))
    aba.update(values=[list(df.columns)] + df.values.tolist(), range_name="A1")
    aba.freeze(rows=1)
    return len(df)


def exportar(nome_planilha="Escritório Contábil - Painel Financeiro"):
    from analise import (
        carregar, dre_mensal, caixa_mensal, inadimplencia_por_cliente,
        projetar_recebimento, ponto_de_equilibrio,
    )

    cl, rc, pg = carregar()
    dre = dre_mensal(rc, pg)
    caixa = caixa_mensal(rc, pg)
    inad = inadimplencia_por_cliente(rc, cl)
    projecao, resumo_proj = projetar_recebimento(rc, inad)
    pe = ponto_de_equilibrio(dre)

    # titulos individuais, base do painel para filtro por cliente e mes
    titulos = rc.merge(
        cl[["id_cliente", "razao_social", "segmento", "plano"]],
        on="id_cliente", how="left")
    titulos = titulos.merge(inad[["id_cliente", "risco"]], on="id_cliente", how="left")

    conexao = _autenticar()
    try:
        planilha = conexao.open(nome_planilha)
    except Exception:
        planilha = conexao.create(nome_planilha)

    abas = {
        "dre_mensal": dre,
        "caixa_mensal": caixa,
        "inadimplencia": inad,
        "titulos": titulos,
        "projecao_recebiveis": projecao,
    }
    for nome, dados in abas.items():
        linhas = _gravar_aba(planilha, nome, dados)
        print(f"{nome:<20} {linhas:>6} linhas")

    # aba de indicadores unicos, formato chave-valor
    pe_df = pd.DataFrame([{"indicador": k, "valor": v} for k, v in pe.items()])
    for k, v in resumo_proj.items():
        pe_df.loc[len(pe_df)] = [k, v]
    _gravar_aba(planilha, "indicadores", pe_df)

    try:
        planilha.del_worksheet(planilha.worksheet("Sheet1"))
    except Exception:
        pass

    print()
    print(f"Planilha disponível em {planilha.url}")
    return planilha.url


if __name__ == "__main__":
    exportar()
