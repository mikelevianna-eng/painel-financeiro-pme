# Painel Financeiro para Pequena Empresa

Por que o mês fecha no vermelho mesmo com contrato assinado, quanto vai entrar de caixa nos próximos 30, 60 e 90 dias, e quanto a empresa precisa faturar para não operar no prejuízo.

Um notebook gera os dados e publica numa planilha do Google. O painel em `index.html` lê essa planilha **ao vivo** e recalcula tudo no navegador. Atualizar os números do painel é rodar o notebook de novo, sem regenerar nenhum arquivo estático.

[![Abrir no Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mikelevianna-eng/painel-financeiro-pme/blob/main/painel_financeiro.ipynb)
[![Ver painel](https://img.shields.io/badge/ver%20painel-ao%20vivo-2563EB?style=flat-square)](https://mikelevianna-eng.github.io/painel-financeiro-pme/)

> ### ⚠️ Dados fictícios
>
> O escritório contábil não existe. Clientes, honorários e lançamentos são gerados por script, já que dados financeiros de empresas reais não podem ser publicados. A metodologia é real e se aplica a qualquer negócio com receita recorrente e inadimplência.

---

## O problema

Empresa de serviço recorrente costuma ter contrato assinado, cliente fiel e ainda assim aperto de caixa. A razão quase sempre é a mesma: o relatório que o dono olha é por competência, mostrando o que foi faturado, não por caixa, mostrando o que efetivamente entrou. Um cliente que atrasa sistematicamente quinze dias faz o resultado do mês parecer bom no papel e ruim na conta corrente.

---

## O que a análise faz

**DRE por competência**, receita e despesa contadas pelo mês a que se referem.

**Fluxo de caixa por regime de caixa**, pela data em que o dinheiro efetivamente mudou de mão. Cruzando os dois, fica visível a distância entre o que foi vendido e o que foi recebido.

**Inadimplência por cliente**, com o atraso médio histórico de cada um e uma classificação de risco.

**Projeção de recebíveis a 30, 60 e 90 dias**, que não usa a data de vencimento contratual como se fosse a data de entrada no caixa. Cada título em aberto é projetado pelo atraso médio do próprio cliente que o deve, porque tratar todo mundo com o mesmo prazo esconde exatamente o cliente que precisa de cobrança ativa.

**Ponto de equilíbrio**, isolando do custo total a parcela que varia com a receita, para saber quanto a empresa precisa faturar por mês para não operar no vermelho.

---

## O painel é vivo, não uma imagem

A maior parte de relatório de dados em portfólio é uma foto do resultado de uma execução. Este não é.

O notebook publica cinco abas numa planilha do Google. O `index.html` lê o CSV publicado dessas abas via `fetch`, recalcula DRE, caixa, inadimplência, projeção e ponto de equilíbrio inteiramente em JavaScript, e desenha os gráficos em SVG puro, sem biblioteca externa.

Isso significa duas coisas. Primeiro, que atualizar a planilha atualiza o painel, sem precisar gerar HTML de novo. Segundo, que a lógica de cálculo existe em dois lugares, pandas no notebook e JavaScript no navegador, e os dois precisam concordar.

**Validação:** cada função em JavaScript foi conferida linha a linha contra a mesma função em pandas, usando o Node.js como ambiente de teste isolado. Os números batem exatamente.

Um bug real apareceu nesse processo e vale contar. A projeção de recebíveis, em JavaScript, inicialmente usava `new Date()`, a data real do sistema, como referência. O notebook em Python usa uma data fixa, o fim do período coberto pela base. Como o painel pode ser aberto qualquer dia, a projeção calculada no navegador saía errada silenciosamente, sem erro nenhum, porque a diferença de dias mudava com o calendário. A correção foi calcular a data de referência a partir do próprio dado carregado, pegando a maior data presente e arredondando para o fim daquele mês, em vez de confiar no relógio do computador de quem abre a página.

---

## Como executar

Abra `painel_financeiro.ipynb` no Colab e rode as células em ordem. Ele gera a base, roda a análise e, na etapa final, publica os resultados no Google Sheets, pedindo autorização uma vez.

Depois de publicar, em cada aba do Sheets: Arquivo, Compartilhar, Publicar na web, escolha a aba e o formato CSV. Cole os dois endereços gerados, um para `titulos` e outro para `contas_pagar`, nas constantes `CSV_TITULOS` e `CSV_PAGAR` no início do `index.html`.

Para usar com dados reais, troque os três CSVs de entrada mantendo os nomes de coluna, e rode o notebook a partir da etapa de análise.

---

## Decisões técnicas

**Competência e caixa são calculados separadamente, nunca misturados.** Somar entradas de caixa com receita de competência no mesmo total produziria um número sem significado contábil.

**A comissão sobre atraso usa o histórico do próprio cliente, com uma mediana geral como piso.** Cliente novo, sem título pago ainda, não tem como ter atraso médio próprio, e cair para zero dias de atraso super-estimaria a velocidade de recebimento dele.

**O ponto de equilíbrio isola o custo fixo do variável antes de dividir**, porque dividir a despesa total pela mesma proporção usada para extrair o fixo cancela a conta algebricamente e devolve exatamente a despesa média, um número sem nenhum valor analítico. Esse erro apareceu numa primeira versão e foi corrigido antes da entrega.

---

## Limitações

O percentual de custo variável sobre a receita é uma premissa assumida, não calculado a partir da composição real dos custos. Num caso real, precisa ser levantado com o cliente.

A projeção de recebíveis assume que o padrão de atraso de cada cliente se mantém estável. Mudança de comportamento recente do cliente não é capturada.

O painel lê duas planilhas publicadas separadamente. Se uma delas for despublicada ou o link expirar, o painel mostra aviso de erro em vez de quebrar silenciosamente.

---

## Estrutura

```
painel-financeiro-pme/
├── painel_financeiro.ipynb   Gera, analisa e publica no Sheets
├── gerar.py                  Gerador da base, usado pelo notebook
├── analise.py                Funções de análise em pandas
├── exportar_sheets.py        Publicação no Google Sheets
└── docs/
    └── index.html            Painel vivo, conectado à planilha
```

---

## Projetos relacionados

- **Casa Verde Distribuidora** — margem de contribuição em comércio, com o mesmo padrão de painel vivo
- **Análise de clientes e agenda** — recorrência e retenção em empresa de serviço
- **Modelagem dimensional em SQL** — o mesmo tipo de análise estruturada em modelo estrela
- **Diagnóstico de qualidade de dados** — a etapa anterior, que avalia se a base está pronta
