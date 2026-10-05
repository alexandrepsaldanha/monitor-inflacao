"""Coleta do IPCA (IBGE/SIDRA) e das expectativas do Focus (Banco Central).

Fontes
------
- SIDRA, tabela 1737: IPCA, variação mensal desde 1980 (variável 63).
- SIDRA, tabela 7060: IPCA por grupo, variação mensal (63) e peso (66), desde 2020.
- Banco Central, API Olinda: expectativas mensais do Focus para o IPCA.
"""

from __future__ import annotations

import re
import time
from datetime import date

import pandas as pd
import requests

SIDRA = "https://apisidra.ibge.gov.br/values"
OLINDA = ("https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
          "ExpectativaMercadoMensais")
TIMEOUT = 120


def _get(url: str, params: dict | None = None, tentativas: int = 4):
    """GET com novas tentativas: as APIs públicas oscilam com frequência."""
    for i in range(tentativas):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if i == tentativas - 1:
                raise
            time.sleep(5 * (i + 1))


def sidra_para_tabela(json_sidra: list[dict]) -> pd.DataFrame:
    """Converte a resposta do SIDRA em tabela com colunas nomeadas.

    A primeira linha da resposta é o cabeçalho: mapeia os códigos D1, D2, ...
    para os nomes das dimensões. As dimensões são identificadas pelo nome, e
    não pela posição, para não depender da ordem da tabela.
    """
    cab, linhas = json_sidra[0], json_sidra[1:]
    df = pd.DataFrame(linhas)
    nomes = {}
    for chave, rotulo in cab.items():
        m = re.fullmatch(r"D(\d+)([CN])", chave)
        if m:
            base = rotulo.replace(" (Código)", "").strip()
            nomes[chave] = base + ("_cod" if m.group(2) == "C" else "")
    df = df.rename(columns=nomes)
    df["valor"] = pd.to_numeric(df["V"], errors="coerce")  # "..." e "-" viram NA
    return df


def _mes(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["Mês_cod"], format="%Y%m")


def ipca_mensal(inicio: str = "1995-01-01") -> pd.DataFrame:
    """IPCA, variação mensal (%), tabela 1737, a partir do Plano Real."""
    df = sidra_para_tabela(_get(f"{SIDRA}/t/1737/n1/all/v/63/p/all"))
    out = pd.DataFrame({"data": _mes(df), "ipca": df["valor"]}).dropna()
    return out[out["data"] >= inicio].sort_values("data").reset_index(drop=True)


def ipca_grupos(ano_inicial: int = 2020) -> pd.DataFrame:
    """Variação mensal e peso dos nove grupos do IPCA, tabela 7060.

    A consulta é feita ano a ano para respeitar o limite de valores do SIDRA.
    """
    hoje = date.today()
    partes = []
    for ano in range(ano_inicial, hoje.year + 1):
        # anos completos por intervalo; o ano corrente pelos últimos meses divulgados
        periodo = f"{ano}01-{ano}12" if ano < hoje.year else f"last%20{hoje.month}"
        js = _get(f"{SIDRA}/t/7060/n1/all/v/63,66/p/{periodo}/c315/all")
        if len(js) > 1:
            partes.append(sidra_para_tabela(js))
    df = pd.concat(partes, ignore_index=True).drop_duplicates()
    col_cat = [c for c in df.columns if c.startswith("Geral") and not c.endswith("_cod")][0]
    # Os grupos têm rótulos como "1.Alimentação e bebidas" (um dígito e ponto)
    grupos = df[df[col_cat].str.match(r"^\d\.\D")].copy()
    grupos["grupo"] = grupos[col_cat].str.replace(r"^\d\.", "", regex=True).str.strip()
    grupos["data"] = _mes(grupos)
    grupos["variavel"] = grupos["Variável_cod"].map({"63": "variacao", "66": "peso"})
    tab = (grupos.pivot_table(index=["data", "grupo"], columns="variavel", values="valor")
           .reset_index().dropna())
    return tab.sort_values(["data", "grupo"]).reset_index(drop=True)


def focus_mensal(desde: str = "2019-01-01") -> pd.DataFrame:
    """Mediana das expectativas mensais do Focus para o IPCA."""
    params = {
        "$filter": f"Indicador eq 'IPCA' and baseCalculo eq 0 and Data ge '{desde}'",
        "$select": "Data,DataReferencia,Mediana,numeroRespondentes",
        "$format": "json",
        "$top": "200000",
    }
    js = _get(OLINDA, params=params)
    df = pd.DataFrame(js["value"])
    df["data_pesquisa"] = pd.to_datetime(df["Data"])
    df["referencia"] = pd.to_datetime(df["DataReferencia"], format="%m/%Y")
    return (df.rename(columns={"Mediana": "mediana", "numeroRespondentes": "respondentes"})
            [["data_pesquisa", "referencia", "mediana", "respondentes"]]
            .drop_duplicates(["data_pesquisa", "referencia"], keep="last")
            .sort_values(["referencia", "data_pesquisa"]).reset_index(drop=True))


def coletar(pasta: str = "data") -> None:
    ipca_mensal().to_csv(f"{pasta}/ipca_mensal.csv", index=False)
    ipca_grupos().to_csv(f"{pasta}/ipca_grupos.csv", index=False)
    focus_mensal().to_csv(f"{pasta}/focus_mensal.csv", index=False)


if __name__ == "__main__":
    coletar()
