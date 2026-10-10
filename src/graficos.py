"""Gráficos do monitor de inflação."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

AZUL, LARANJA, VERDE, AMARELO, ROSA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
CINZA, TINTA, TINTA2 = "#8a8a8a", "#1f1f1f", "#5c5c5c"
CORES_CATEGORIAS = {
    "Alimentação e bebidas": AZUL,
    "Habitação": LARANJA,
    "Transportes": VERDE,
    "Saúde e cuidados pessoais": AMARELO,
    "Demais grupos": ROSA,
}
FONTE = "Fonte: IBGE (IPCA) e Banco Central (Focus). Elaboração própria."
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def mes_ano(d) -> str:
    return f"{MESES[d.month - 1]}/{d.strftime('%y')}"


def _fmt_mes(x, _):
    return mes_ano(mdates.num2date(x))


def _estilo(ax, titulo: str, subtitulo: str | None = None):
    ax.set_title(titulo, loc="left", fontsize=13, fontweight="bold", color=TINTA, pad=22 if subtitulo else 10)
    if subtitulo:
        ax.text(0, 1.02, subtitulo, transform=ax.transAxes, fontsize=9.5, color=TINTA2)
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(colors=TINTA2, labelsize=9)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.1f}".replace(".", ","))


def _rodape(fig):
    fig.text(0.01, 0.01, FONTE, fontsize=8, color=TINTA2)


def acumulado(ac: pd.DataFrame, proj_ac: pd.DataFrame | None, caminho: str, desde: str = "2017-01-01"):
    d = ac[ac["data"] >= desde]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.fill_between(d["data"], d["meta"] - 1.5, d["meta"] + 1.5, step="mid", color="#ececec",
                    label="Intervalo de tolerância da meta")
    ax.step(d["data"], d["meta"], where="mid", color=CINZA, linewidth=1.2, linestyle="--", label="Centro da meta")
    ax.plot(d["data"], d["acum_12m"], color=AZUL, linewidth=2, label="IPCA acumulado em 12 meses")
    if proj_ac is not None:
        ligacao = pd.concat([d.tail(1)[["data", "acum_12m"]], proj_ac])
        ax.plot(ligacao["data"], ligacao["acum_12m"], color=AZUL, linewidth=2, linestyle=":",
                label="Projeção (SARIMA)")
    ult = d.iloc[-1]
    ax.annotate(f"{ult['acum_12m']:.2f}%".replace(".", ","), (ult["data"], ult["acum_12m"]),
                xytext=(6, 4), textcoords="offset points", fontsize=9, color=TINTA, fontweight="bold")
    _estilo(ax, "IPCA acumulado em 12 meses e meta de inflação", "% em 12 meses")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.08), ncol=4)
    _rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def contribuicoes(contrib: pd.DataFrame, ipca: pd.DataFrame, caminho: str, meses: int = 12):
    datas = sorted(contrib["data"].unique())[-meses:]
    tab = (contrib[contrib["data"].isin(datas)]
           .pivot(index="data", columns="categoria", values="contribuicao")
           [list(CORES_CATEGORIAS)].fillna(0))
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = range(len(tab))
    pos = [0.0] * len(tab)
    neg = [0.0] * len(tab)
    for cat, cor in CORES_CATEGORIAS.items():
        v = tab[cat].values
        base = [p if val >= 0 else n for val, p, n in zip(v, pos, neg)]
        ax.bar(x, v, bottom=base, color=cor, width=0.7, edgecolor="white", linewidth=1, label=cat)
        pos = [p + max(val, 0) for p, val in zip(pos, v)]
        neg = [n + min(val, 0) for n, val in zip(neg, v)]
    geral = ipca.set_index("data").loc[tab.index, "ipca"].values
    ax.plot(list(x), geral, "o", color=TINTA, markersize=5, label="IPCA (índice geral)")
    for xi, g in zip(x, geral):
        ax.annotate(f"{g:.2f}".replace(".", ","), (xi, g), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=7.5, color=TINTA)
    ax.axhline(0, color=TINTA2, linewidth=0.8)
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.12 * (hi - lo))
    ax.set_xticks(list(x), [mes_ano(d) for d in tab.index], fontsize=8.5)
    _estilo(ax, "Contribuição dos grupos para o IPCA mensal", "pontos percentuais; peso × variação do grupo")
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.1))
    _rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def projecao(ipca: pd.DataFrame, proj: pd.DataFrame, focus_futuro: pd.DataFrame, caminho: str, meses: int = 24):
    hist = ipca.tail(meses)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(hist["data"], hist["ipca"], color=AZUL, linewidth=2, label="IPCA observado")
    ligacao = pd.concat([hist.tail(1).rename(columns={"ipca": "sarima"})[["data", "sarima"]],
                         proj[["data", "sarima"]]])
    ax.fill_between(proj["data"], proj["ic80_inf"], proj["ic80_sup"], color=AZUL, alpha=0.12,
                    label="Intervalo de 80%")
    ax.plot(ligacao["data"], ligacao["sarima"], color=AZUL, linewidth=2, linestyle=":", label="Projeção SARIMA")
    if len(focus_futuro):
        ax.plot(focus_futuro["data"], focus_futuro["focus"], "o", color=LARANJA, markersize=7,
                markeredgecolor="white", markeredgewidth=1.5, label="Mediana do Focus")
    ax.axhline(0, color=TINTA2, linewidth=0.8)
    _estilo(ax, "IPCA mensal: observado e projeção para os próximos meses", "% ao mês")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(_fmt_mes)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.08), ncol=4)
    _rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def _br(v: float, d: int = 2) -> str:
    return f"{v:.{d}f}".replace(".", ",").replace("-", "−")


def trajetoria_focus(traj: pd.DataFrame, mes, observado: float, meio_mes: float | None, caminho: str):
    """Mediana do Focus para um mês, pesquisa a pesquisa, contra o IPCA divulgado."""
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(traj["data_pesquisa"], traj["mediana"], color=AZUL, linewidth=2, drawstyle="steps-post",
            label="Mediana do Focus para o mês")
    ult = traj.iloc[-1]
    ax.plot([ult["data_pesquisa"]], [ult["mediana"]], "o", color=AZUL, markersize=6)
    ax.annotate(f"Última pesquisa: {_br(ult['mediana'])}%", (ult["data_pesquisa"], ult["mediana"]),
                xytext=(-8, 10), textcoords="offset points", ha="right", fontsize=9, color=AZUL)
    if meio_mes is not None and pd.notna(meio_mes):
        meio = traj[(traj["data_pesquisa"].dt.to_period("M") == pd.Timestamp(mes).to_period("M")) &
                    (traj["data_pesquisa"].dt.day >= 15)].head(1)
        if len(meio):
            ax.plot(meio["data_pesquisa"], meio["mediana"], "o", color=TINTA2, markersize=6,
                    markerfacecolor="white", markeredgewidth=1.5, label="Pesquisa do meio do mês")
    ax.axhline(observado, color=LARANJA, linewidth=2, linestyle="--", label=f"IPCA divulgado: {_br(observado)}%")
    ax.axvspan(pd.Timestamp(mes), pd.Timestamp(mes) + pd.offsets.MonthEnd(0), color="#f2f2f2", zorder=0)
    ax.text(pd.Timestamp(mes) + pd.Timedelta(days=2), 0.97, "mês de referência", transform=ax.get_xaxis_transform(),
            fontsize=8, color=TINTA2, va="top")
    _estilo(ax, f"Quanto o mercado esperava para o IPCA de {mes_ano(pd.Timestamp(mes))}",
            "% ao mês; mediana das expectativas do Focus em cada pesquisa até a divulgação")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.2f}".replace(".", ","))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(_fmt_mes)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.08), ncol=3)
    _rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def historico_surpresas(s: pd.DataFrame, caminho: str):
    """Erro do Focus em cada mês: IPCA divulgado menos a mediana da véspera."""
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = range(len(s))
    cores = [LARANJA if v > 0 else AZUL for v in s["surpresa"]]
    alfas = [1.0 if i == len(s) - 1 else 0.55 for i in x]
    for xi, v, c, a in zip(x, s["surpresa"], cores, alfas):
        ax.bar(xi, v, color=c, alpha=a, width=0.75, edgecolor=TINTA if a == 1.0 else "none", linewidth=1.2)
    dp = s["surpresa"].std()
    for y in (dp, -dp):
        ax.axhline(y, color=CINZA, linestyle=":", linewidth=1)
    ax.text(-0.5, dp, "±1 desvio-padrão", fontsize=8, color=TINTA2, va="bottom", ha="left")
    ax.axhline(0, color=TINTA2, linewidth=0.8)
    u = s.iloc[-1]
    ax.annotate(f"{mes_ano(u['data'])}: {_br(u['surpresa'])} p.p.", (len(s) - 1, u["surpresa"]),
                xytext=(0, 8 if u["surpresa"] > 0 else -14), textcoords="offset points", ha="center",
                fontsize=9, fontweight="bold", color=TINTA)
    pos = list(range(len(s) - 1, -1, -3))[::-1]
    ax.set_xticks(pos, [mes_ano(s["data"].iloc[i]) for i in pos], fontsize=8.5)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.1f}".replace(".", ",").replace("-", "−"))
    _estilo(ax, "Surpresas do IPCA em relação ao Focus",
            "p.p.; IPCA divulgado menos a última mediana do Focus. Laranja: mercado subestimou; azul: superestimou")
    _rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(caminho, dpi=200)
    plt.close(fig)
