"""Decomposição do IPCA, projeção de curto prazo e comparação com o Focus."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Centro da meta de inflação (CMN) e intervalo de tolerância
META = {2017: 4.5, 2018: 4.5, 2019: 4.25, 2020: 4.0, 2021: 3.75,
        2022: 3.5, 2023: 3.25, 2024: 3.0}
META_CONTINUA = 3.0      # meta contínua a partir de 2025
TOLERANCIA = 1.5

AGREGACAO = {
    "Alimentação e bebidas": "Alimentação e bebidas",
    "Habitação": "Habitação",
    "Transportes": "Transportes",
    "Saúde e cuidados pessoais": "Saúde e cuidados pessoais",
}
DEMAIS = "Demais grupos"


def meta(ano: int) -> float:
    return META.get(ano, META_CONTINUA)


# ---------------------------------------------------------------------------
# Acumulados e decomposição
# ---------------------------------------------------------------------------

def acumulado_12m(ipca: pd.DataFrame) -> pd.DataFrame:
    """Inflação acumulada em 12 meses (%) a partir das variações mensais."""
    s = ipca.set_index("data")["ipca"]
    ac = ((1 + s / 100).rolling(12).apply(np.prod, raw=True) - 1) * 100
    out = ac.dropna().rename("acum_12m").reset_index()
    out["meta"] = out["data"].dt.year.map(meta)
    return out


def contribuicoes(grupos: pd.DataFrame) -> pd.DataFrame:
    """Contribuição de cada grupo para a variação mensal (p.p.) = peso × variação / 100."""
    g = grupos.copy()
    g["contribuicao"] = g["peso"] * g["variacao"] / 100
    g["categoria"] = g["grupo"].map(AGREGACAO).fillna(DEMAIS)
    return (g.groupby(["data", "categoria"], as_index=False)["contribuicao"].sum()
            .sort_values(["data", "categoria"]))


def conferir_decomposicao(contrib: pd.DataFrame, ipca: pd.DataFrame) -> pd.DataFrame:
    """Compara a soma das contribuições com o índice geral divulgado."""
    soma = contrib.groupby("data", as_index=False)["contribuicao"].sum()
    out = soma.merge(ipca, on="data")
    out["diferenca"] = out["contribuicao"] - out["ipca"]
    return out


# ---------------------------------------------------------------------------
# Modelos de projeção
# ---------------------------------------------------------------------------

def _sarima(y: pd.Series):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return SARIMAX(y, order=(1, 0, 1), seasonal_order=(1, 0, 1, 12),
                       trend="c").fit(disp=False)


def _sazonal(y: pd.Series, h: int, anos: int = 5) -> np.ndarray:
    """Referência simples: média dos últimos 12 meses + efeito médio do mês do ano."""
    recente = y.iloc[-12:].mean()
    hist = y.iloc[-12 * anos:]
    efeito = (hist - hist.rolling(12, center=True, min_periods=6).mean()).groupby(hist.index.month).mean()
    meses = pd.date_range(y.index[-1] + pd.offsets.MonthBegin(), periods=h, freq="MS").month
    return np.array([recente + efeito.get(m, 0.0) for m in meses])


def projetar(ipca: pd.DataFrame, h: int = 6, inicio: str = "2004-01-01") -> pd.DataFrame:
    """Projeção dos próximos h meses pelo SARIMA, com intervalo de 80%."""
    y = ipca.set_index("data")["ipca"].loc[inicio:].asfreq("MS")
    fit = _sarima(y)
    prev = fit.get_forecast(h)
    ic = prev.conf_int(alpha=0.2)
    return pd.DataFrame({
        "data": prev.predicted_mean.index,
        "sarima": prev.predicted_mean.values,
        "ic80_inf": ic.iloc[:, 0].values,
        "ic80_sup": ic.iloc[:, 1].values,
        "sazonal": _sazonal(y, h),
    })


def focus_no_meio_do_mes(focus: pd.DataFrame) -> pd.DataFrame:
    """Mediana do Focus para cada mês, coletada na metade do próprio mês.

    Nesse momento o IPCA do mês anterior já foi divulgado (por volta do dia 10),
    o mesmo conjunto de informação usado pelos modelos.
    """
    f = focus[focus["data_pesquisa"].dt.to_period("M") == focus["referencia"].dt.to_period("M")]
    f = f[f["data_pesquisa"].dt.day >= 15]
    return (f.sort_values("data_pesquisa").groupby("referencia", as_index=False).first()
            .rename(columns={"referencia": "data", "mediana": "focus"})[["data", "focus"]])


def focus_vespera(focus: pd.DataFrame) -> pd.DataFrame:
    """Última mediana do Focus para cada mês antes da divulgação do IPCA.

    A pesquisa segue coletando expectativas para um mês até a véspera da
    divulgação do índice; a última coleta é o consenso final do mercado.
    """
    f = focus.sort_values("data_pesquisa").groupby("referencia", as_index=False).last()
    return f.rename(columns={"referencia": "data", "mediana": "focus_vespera",
                             "data_pesquisa": "pesquisa_vespera"})[["data", "focus_vespera", "pesquisa_vespera"]]


def surpresas(ipca: pd.DataFrame, focus: pd.DataFrame, meses: int = 36) -> pd.DataFrame:
    """Erro do Focus (IPCA observado menos mediana) nos últimos meses.

    Duas referências: a mediana da véspera da divulgação (o consenso final do
    mercado) e a do meio do mês (mesmo conjunto de informação dos modelos).
    """
    s = (ipca.merge(focus_vespera(focus), on="data")
         .merge(focus_no_meio_do_mes(focus), on="data", how="left"))
    s["surpresa"] = s["ipca"] - s["focus_vespera"]
    s["surpresa_meio_mes"] = s["ipca"] - s["focus"]
    return s.sort_values("data").tail(meses).reset_index(drop=True)


def trajetoria(focus: pd.DataFrame, mes, meses_antes: int = 4) -> pd.DataFrame:
    """Evolução da mediana do Focus para um mês, nas pesquisas anteriores à divulgação."""
    mes = pd.Timestamp(mes)
    f = focus[(focus["referencia"] == mes) &
              (focus["data_pesquisa"] >= mes - pd.DateOffset(months=meses_antes))]
    return f.sort_values("data_pesquisa")[["data_pesquisa", "mediana"]].reset_index(drop=True)


def avaliar_fora_da_amostra(ipca: pd.DataFrame, focus: pd.DataFrame, meses: int = 36,
                            inicio: str = "2004-01-01") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Previsões um passo à frente em janela crescente, comparadas ao Focus."""
    y = ipca.set_index("data")["ipca"].loc[inicio:].asfreq("MS")
    linhas = []
    for t in y.index[-meses:]:
        treino = y.loc[:t - pd.offsets.MonthBegin()]
        linhas.append({"data": t, "ipca": y.loc[t],
                       "sarima": float(_sarima(treino).forecast(1).iloc[0]),
                       "sazonal": float(_sazonal(treino, 1)[0])})
    prev = pd.DataFrame(linhas).merge(focus_no_meio_do_mes(focus), on="data", how="left")
    comuns = prev.dropna()
    metr = []
    for m in ["focus", "sarima", "sazonal"]:
        e = comuns[m] - comuns["ipca"]
        metr.append({"modelo": m, "rmse": np.sqrt((e ** 2).mean()), "mae": e.abs().mean(),
                     "vies": e.mean(), "n": len(e)})
    return prev, pd.DataFrame(metr)


def acumulado_projetado(ipca: pd.DataFrame, proj: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Acumulado em 12 meses combinando o observado com a projeção."""
    s = pd.concat([ipca.set_index("data")["ipca"], proj.set_index("data")[coluna]])
    ac = ((1 + s / 100).rolling(12).apply(np.prod, raw=True) - 1) * 100
    return ac.loc[proj["data"]].rename("acum_12m").reset_index()
