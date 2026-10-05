"""Executa o monitor: coleta, análise, projeção, gráficos e nota mensal.

Uso, a partir da raiz do repositório:
    python src/main.py            # coleta os dados e gera tudo
    python src/main.py --sem-coleta   # usa os CSVs já existentes em data/
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import analise  # noqa: E402
import coleta  # noqa: E402
import graficos  # noqa: E402
from graficos import mes_ano  # noqa: E402

DATA, FIG, TAB = "data", "output/figuras", "output/tabelas"


def br(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def carregar():
    ipca = pd.read_csv(f"{DATA}/ipca_mensal.csv", parse_dates=["data"])
    grupos = pd.read_csv(f"{DATA}/ipca_grupos.csv", parse_dates=["data"])
    focus = pd.read_csv(f"{DATA}/focus_mensal.csv", parse_dates=["data_pesquisa", "referencia"])
    return ipca, grupos, focus


def focus_futuro(focus: pd.DataFrame, ultimo_mes) -> pd.DataFrame:
    """Medianas da pesquisa Focus mais recente para os meses ainda não divulgados."""
    ultima = focus["data_pesquisa"].max()
    f = focus[(focus["data_pesquisa"] == ultima) & (focus["referencia"] > ultimo_mes)]
    return (f.rename(columns={"referencia": "data", "mediana": "focus"})[["data", "focus"]]
            .drop_duplicates("data", keep="last"))


def nota(ipca, ac, contrib, proj, proj_ac, ff, prev_aval, metricas, focus_ref, prox12) -> str:
    ult = ipca.iloc[-1]
    mes = ult["data"]
    ac_ult = ac.iloc[-1]
    no_ano = ipca[ipca["data"].dt.year == mes.year]["ipca"]
    ac_ano = ((1 + no_ano / 100).prod() - 1) * 100
    teto = ac_ult["meta"] + analise.TOLERANCIA
    esperado = focus_ref.loc[focus_ref["data"] == mes, "focus"]
    surpresa = (f"A mediana do Focus coletada no meio do mês esperava {br(esperado.iloc[0])}%: "
                f"surpresa de {br(ult['ipca'] - esperado.iloc[0])} p.p."
                if len(esperado) else "Sem expectativa do Focus disponível para o mês.")

    c_mes = contrib[contrib["data"] == mes].set_index("categoria")["contribuicao"]
    datas12 = sorted(contrib["data"].unique())[-12:]
    c_12 = contrib[contrib["data"].isin(datas12)].groupby("categoria")["contribuicao"].sum()
    ordem = list(graficos.CORES_CATEGORIAS)
    linhas_c = "\n".join(f"| {c} | {br(c_mes.get(c, 0))} | {br(c_12.get(c, 0))} |" for c in ordem)

    p = proj.merge(ff, on="data", how="left").merge(proj_ac.rename(columns={"acum_12m": "ac"}), on="data")
    linhas_p = "\n".join(
        f"| {mes_ano(r.data)} | {br(r.sarima)} | {br(r.ic80_inf)} a {br(r.ic80_sup)} | "
        f"{br(r.focus) if pd.notna(r.focus) else '–'} | {br(r.ac)} |" for r in p.itertuples())

    nomes = {"focus": "Mediana do Focus", "sarima": "SARIMA", "sazonal": "Sazonal simples"}
    linhas_m = "\n".join(f"| {nomes[r.modelo]} | {br(r.rmse, 3)} | {br(r.mae, 3)} | {br(r.vies, 3)} |"
                         for r in metricas.sort_values("rmse").itertuples())
    n_aval = int(metricas["n"].iloc[0])

    leitura = ""
    if os.path.exists("nota/leitura.md"):
        leitura = "\n## Leitura\n\n" + open("nota/leitura.md", encoding="utf-8").read().strip() + "\n"

    return f"""# Monitor de inflação: IPCA de {mes_ano(mes)}

*Atualizado automaticamente após a divulgação do IPCA pelo IBGE.*

## Destaques

- **IPCA de {mes_ano(mes)}: {br(ult['ipca'])}%.** {surpresa}
- **Acumulado em 12 meses: {br(ac_ult['acum_12m'])}%**, para uma meta de {br(ac_ult['meta'], 1)}% e teto de {br(teto, 1)}%{" (acima do teto)" if ac_ult['acum_12m'] > teto else ""}.
- **Acumulado no ano: {br(ac_ano)}%.**
- **Inflação projetada para os próximos 12 meses (SARIMA, até {mes_ano(prox12['data'])}): {br(prox12['acum_12m'])}%.**
{leitura}
## Contribuições por grupo

| Grupo | {mes_ano(mes)} (p.p.) | Soma dos últimos 12 meses (p.p.) |
|---|---:|---:|
{linhas_c}

![Contribuições](../output/figuras/contribuicoes.png)

## Projeção

| Mês | SARIMA (%) | Intervalo de 80% | Focus, mediana (%) | Acumulado em 12 meses, SARIMA (%) |
|---|---:|---:|---:|---:|
{linhas_p}

![Projeção](../output/figuras/projecao.png)

### Desempenho fora da amostra

Previsões um passo à frente nos últimos {n_aval} meses, em pontos percentuais. A mediana do Focus é a coletada na metade do mês de referência, quando o IPCA do mês anterior já é conhecido, o mesmo conjunto de informação dos modelos.

| Modelo | RMSE | MAE | Viés |
|---|---:|---:|---:|
{linhas_m}

![IPCA em 12 meses](../output/figuras/acumulado_12m.png)
"""


def main(coletar: bool = True):
    for d in (DATA, FIG, TAB, "nota"):
        os.makedirs(d, exist_ok=True)
    if coletar:
        coleta.coletar(DATA)
    ipca, grupos, focus = carregar()

    ac = analise.acumulado_12m(ipca)
    contrib = analise.contribuicoes(grupos)
    conf = analise.conferir_decomposicao(contrib, ipca)
    proj = analise.projetar(ipca, h=12)
    proj_ac = analise.acumulado_projetado(ipca, proj, "sarima")
    prev_aval, metricas = analise.avaliar_fora_da_amostra(ipca, focus)
    focus_ref = analise.focus_no_meio_do_mes(focus)
    ff = focus_futuro(focus, ipca["data"].max())

    ac.to_csv(f"{TAB}/acumulado_12m.csv", index=False)
    contrib.to_csv(f"{TAB}/contribuicoes.csv", index=False)
    conf.to_csv(f"{TAB}/conferencia_decomposicao.csv", index=False)
    proj.merge(proj_ac, on="data").to_csv(f"{TAB}/projecao.csv", index=False)
    prev_aval.to_csv(f"{TAB}/previsoes_fora_da_amostra.csv", index=False)
    metricas.to_csv(f"{TAB}/metricas_fora_da_amostra.csv", index=False)

    graficos.acumulado(ac, proj_ac, f"{FIG}/acumulado_12m.png")
    graficos.contribuicoes(contrib, ipca, f"{FIG}/contribuicoes.png")
    graficos.projecao(ipca, proj.head(6), ff[ff["data"].isin(proj.head(6)["data"])], f"{FIG}/projecao.png")

    with open("nota/ultima_nota.md", "w", encoding="utf-8") as fh:
        fh.write(nota(ipca, ac, contrib, proj.head(6), proj_ac.head(6), ff, prev_aval, metricas, focus_ref,
                     proj_ac.iloc[-1]))
    print(f"Monitor atualizado: IPCA de {mes_ano(ipca['data'].max())}. "
          f"Maior diferença da decomposição: {conf['diferenca'].abs().max():.3f} p.p.")


if __name__ == "__main__":
    main(coletar="--sem-coleta" not in sys.argv)
