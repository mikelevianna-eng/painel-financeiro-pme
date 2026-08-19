"""Gera a base financeira fictícia de um escritório de contabilidade."""

import random
from datetime import date, timedelta

import pandas as pd

SEED = 21
random.seed(SEED)

INICIO = date(2024, 1, 1)
FIM = date(2025, 12, 31)
N_CLIENTES = 58

PRIMEIROS = ["Alfa", "Bravo", "Cedro", "Delta", "Estrela", "Fluxo", "Girassol",
             "Horizonte", "Ipê", "Jangada", "Kappa", "Luminar", "Meridiano", "Norte",
             "Oliva", "Pampa", "Quero", "Raiz", "Serra", "Trevo", "União", "Vetor"]
SEGUNDOS = ["Comércio", "Serviços", "Alimentos", "Construções", "Logística",
            "Tecnologia", "Confecções", "Distribuidora", "Consultoria", "Indústria"]
SUFIXOS = ["Ltda", "ME", "EIRELI", "Ltda ME"]

SEGMENTOS = ["Varejo", "Serviços", "Indústria", "Construção Civil", "Saúde"]

# planos de honorário mensal do escritorio
PLANOS = [("Básico", 350.0, 0.40), ("Intermediário", 650.0, 0.38), ("Completo", 1100.0, 0.22)]


def gerar_clientes():
    clientes, usados = [], set()
    for i in range(N_CLIENTES):
        for _ in range(80):
            nome = f"{random.choice(PRIMEIROS)} {random.choice(SEGUNDOS)} {random.choice(SUFIXOS)}"
            if nome not in usados:
                break
        usados.add(nome)

        plano = random.choices(PLANOS, [p[2] for p in PLANOS])[0]
        # cada cliente tem um perfil de pagamento que se repete ao longo do tempo
        perfil = random.choices(
            ["pontual", "atraso_leve", "atraso_frequente", "inadimplente"],
            [0.55, 0.28, 0.12, 0.05]
        )[0]

        dias_entrada = random.randint(0, 500)
        clientes.append({
            "id_cliente": 3000 + i,
            "razao_social": nome,
            "segmento": random.choice(SEGMENTOS),
            "plano": plano[0],
            "honorario_mensal": plano[1],
            "data_inicio_contrato": INICIO + timedelta(days=dias_entrada),
            "perfil_pagamento": perfil,
        })
    return pd.DataFrame(clientes)


# media de dias de atraso e desvio, por perfil
ATRASO = {
    "pontual":            (0, 1),
    "atraso_leve":        (6, 4),
    "atraso_frequente":   (18, 9),
    "inadimplente":       (55, 25),
}
# chance de o mes ficar em aberto (nao pago ate o fim da base)
PROB_ABERTO = {"pontual": 0.01, "atraso_leve": 0.03, "atraso_frequente": 0.10, "inadimplente": 0.35}


def gerar_contas_receber(clientes):
    linhas, idc = [], 900000
    for _, c in clientes.iterrows():
        mes = date(c["data_inicio_contrato"].year, c["data_inicio_contrato"].month, 5)
        while mes <= FIM:
            if mes >= c["data_inicio_contrato"]:
                vencimento = mes
                media, desvio = ATRASO[c["perfil_pagamento"]]

                em_aberto = (mes > date(2025, 10, 1) and
                            random.random() < PROB_ABERTO[c["perfil_pagamento"]])

                if em_aberto:
                    pagamento = None
                    status = "Em aberto"
                else:
                    atraso = max(0, round(random.gauss(media, desvio)))
                    pagamento = vencimento + timedelta(days=atraso)
                    if pagamento > FIM:
                        pagamento = None
                        status = "Em aberto"
                    else:
                        status = "Pago"

                linhas.append({
                    "id_titulo": idc,
                    "id_cliente": c["id_cliente"],
                    "competencia": mes.strftime("%Y-%m"),
                    "data_vencimento": vencimento,
                    "data_pagamento": pagamento,
                    "valor": c["honorario_mensal"],
                    "status": status,
                })
                idc += 1

            # proximo mes
            if mes.month == 12:
                mes = date(mes.year + 1, 1, 5)
            else:
                mes = date(mes.year, mes.month + 1, 5)

    return pd.DataFrame(linhas)


# despesas fixas mensais do escritorio
DESPESAS_FIXAS = [
    ("Folha de pagamento", 12800.0, 0.02),
    ("Aluguel e condomínio", 2600.0, 0.00),
    ("Softwares e assinaturas", 780.0, 0.02),
    ("Contabilidade própria e taxas", 420.0, 0.01),
    ("Internet e telefonia", 260.0, 0.01),
    ("Marketing e comercial", 500.0, 0.15),
]

# despesas variaveis, como percentual da receita realizada do mes
DESPESAS_VARIAVEIS_PCT = 0.06  # comissao de indicacao e material de trabalho


def gerar_contas_pagar():
    linhas, idp = [], 700000
    mes = date(INICIO.year, INICIO.month, 1)
    valores = {d[0]: d[1] for d in DESPESAS_FIXAS}

    while mes <= FIM:
        for nome, valor_base, variacao in DESPESAS_FIXAS:
            valores[nome] *= (1 + random.uniform(-variacao, variacao * 1.6))
            linhas.append({
                "id_lancamento": idp,
                "categoria": nome,
                "competencia": mes.strftime("%Y-%m"),
                "data_vencimento": date(mes.year, mes.month, random.choice([5, 10, 15, 20])),
                "valor": round(valores[nome], 2),
                "tipo": "Fixa",
            })
            idp += 1

        if mes.month == 12:
            mes = date(mes.year + 1, 1, 1)
        else:
            mes = date(mes.year, mes.month + 1, 1)

    return pd.DataFrame(linhas)


def main():
    clientes = gerar_clientes()
    receber = gerar_contas_receber(clientes)
    pagar = gerar_contas_pagar()

    clientes.to_csv("clientes.csv", index=False, encoding="utf-8")
    receber.to_csv("contas_receber.csv", index=False, encoding="utf-8")
    pagar.to_csv("contas_pagar.csv", index=False, encoding="utf-8")

    print(f"clientes.csv         {len(clientes):>6} linhas")
    print(f"contas_receber.csv   {len(receber):>6} linhas")
    print(f"contas_pagar.csv     {len(pagar):>6} linhas")
    print()
    print(receber["status"].value_counts().to_string())
    pago = receber[receber["status"] == "Pago"]
    print()
    print(f"faturado total   R$ {receber['valor'].sum():,.2f}")
    print(f"recebido total   R$ {pago['valor'].sum():,.2f}")
    print(f"em aberto        R$ {receber[receber.status=='Em aberto']['valor'].sum():,.2f}")
    print(f"despesas totais  R$ {pagar['valor'].sum():,.2f}")


if __name__ == "__main__":
    main()
