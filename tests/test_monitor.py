"""Teste de ponta a ponta com respostas simuladas no formato das APIs do SIDRA e do Focus.

As respostas reais não são acessadas: a função de download é substituída por
uma que devolve JSON com a mesma estrutura (cabeçalho do SIDRA, rótulos de
grupos misturados a subgrupos e subitens, envelope OData do Focus).
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "src"))
import coleta  # noqa: E402
import main  # noqa: E402

GRUPOS = ["Alimentação e bebidas", "Habitação", "Artigos de residência", "Vestuário", "Transportes",
          "Saúde e cuidados pessoais", "Despesas pessoais", "Educação", "Comunicação"]
PESOS = [21.0, 15.0, 4.0, 4.5, 20.5, 13.5, 10.5, 6.0, 5.0]   # somam 100


def _serie(n, seed=1):
    rng = np.random.default_rng(seed)
    meses = pd.date_range("1995-01-01", periods=n, freq="MS")
    saz = np.array([.5, .4, .3, .3, .2, .1, .1, .2, .3, .4, .4, .6]) - 0.3
    return meses, 0.4 + saz[meses.month - 1] + rng.normal(0, .15, n)


MESES, IPCA = _serie(12 * 31 + 8)          # jan/1995 a set/2026
CAB_1737 = {"NC": "Nível Territorial (Código)", "NN": "Nível Territorial", "MC": "Unidade de Medida (Código)",
            "MN": "Unidade de Medida", "V": "Valor", "D1C": "Brasil (Código)", "D1N": "Brasil",
            "D2C": "Variável (Código)", "D2N": "Variável", "D3C": "Mês (Código)", "D3N": "Mês"}
CAB_7060 = dict(CAB_1737, D4C="Geral, grupo, subgrupo, item e subitem (Código)",
                D4N="Geral, grupo, subgrupo, item e subitem")


def _linha(m, var, valor, extra=None):
    d = {"NC": "1", "NN": "Brasil", "MC": "2", "MN": "%", "V": valor, "D1C": "1", "D1N": "Brasil",
         "D2C": var, "D2N": "x", "D3C": m.strftime("%Y%m"), "D3N": "x"}
    return d | (extra or {})


def falso_get(url, params=None, tentativas=4):
    if "/t/1737/" in url:
        return [CAB_1737] + [_linha(m, "63", f"{v:.2f}") for m, v in zip(MESES, IPCA)] + \
               [_linha(pd.Timestamp("1994-12-01"), "63", "...")]
    if "/t/7060/" in url:
        periodo = url.split("/p/")[1].split("/")[0]
        if periodo.startswith("last"):
            k = int(periodo.split("%20")[1]); sel = MESES[-k:]
        else:
            ano = int(periodo[:4]); sel = MESES[MESES.year == ano]
        out = [CAB_7060]
        for m in sel:
            v_geral = IPCA[MESES.get_loc(m)]
            ruido = np.random.default_rng(m.month + m.year).normal(0, .2, 9)
            ruido -= np.average(ruido, weights=PESOS)          # média ponderada = índice geral
            for i, (g, p) in enumerate(zip(GRUPOS, PESOS)):
                for rot, cod in [(f"{i+1}.{g}", str(7170 + i)), (f"{i+1}1.Subgrupo {g}", str(8000 + i)),
                                 (f"{i+1}101.Subitem {g}", str(9000 + i))]:
                    out.append(_linha(m, "63", f"{v_geral + ruido[i]:.2f}", {"D4C": cod, "D4N": rot}))
                    out.append(_linha(m, "66", f"{p:.4f}", {"D4C": cod, "D4N": rot}))
            out.append(_linha(m, "63", f"{v_geral:.2f}", {"D4C": "7169", "D4N": "Índice geral"}))
        return out
    if "Expectativa" in url:
        linhas = []
        for d in pd.date_range("2019-01-01", "2026-10-02", freq="W-FRI"):
            for k in range(0, 13):
                ref = (d + pd.offsets.MonthBegin(k - 1)).normalize().replace(day=1)
                if ref in MESES:
                    base = IPCA[MESES.get_loc(ref)] + np.random.default_rng(d.day).normal(0, .1)
                else:
                    base = 0.35
                for bc in (0, 1):
                    linhas.append({"Data": d.strftime("%Y-%m-%d"), "DataReferencia": ref.strftime("%m/%Y"),
                                   "Mediana": round(base, 2) + bc, "numeroRespondentes": 50, "baseCalculo": bc})
        return {"@odata.context": "x", "value": linhas}
    raise AssertionError(url)


@pytest.fixture()
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(coleta, "_get", falso_get)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_parser_sidra_ignora_valores_nao_numericos():
    df = coleta.sidra_para_tabela(falso_get("/t/1737/"))
    assert {"Mês_cod", "Variável_cod", "valor"} <= set(df.columns)
    assert df["valor"].isna().sum() == 1


def test_focus_url_sem_mais_e_refaz_sem_basecalculo(monkeypatch):
    urls = []

    def get(url, params=None, tentativas=4):
        urls.append(url)
        assert "+" not in url and params is None
        if "baseCalculo" in url.split("%24select")[0] and len(urls) == 1:
            r = coleta.requests.Response(); r.status_code = 400
            raise coleta.requests.HTTPError("400", response=r)
        return falso_get(url)

    monkeypatch.setattr(coleta, "_get", get)
    f = coleta.focus_mensal()
    assert len(urls) == 2 and "%20" in urls[0]
    assert not f.duplicated(["data_pesquisa", "referencia"]).any()
    assert f["mediana"].max() < 1.5                       # só baseCalculo = 0


def test_grupos_filtra_so_os_nove_grupos(pasta):
    g = coleta.ipca_grupos()
    assert sorted(g["grupo"].unique()) == sorted(GRUPOS)
    assert np.allclose(g.groupby("data")["peso"].sum(), 100)


def test_monitor_completo(pasta):
    main.main(coletar=True)
    for f in ["data/ipca_mensal.csv", "data/ipca_grupos.csv", "data/focus_mensal.csv",
              "output/figuras/acumulado_12m.png", "output/figuras/contribuicoes.png",
              "output/figuras/projecao.png", "nota/ultima_nota.md", "output/tabelas/metricas_fora_da_amostra.csv"]:
        assert os.path.exists(f), f
    conf = pd.read_csv("output/tabelas/conferencia_decomposicao.csv")
    assert conf["diferenca"].abs().max() < 0.02          # contribuições somam o índice geral
    nota = open("nota/ultima_nota.md", encoding="utf-8").read()
    assert "IPCA de ago/26" in nota and "nan" not in nota.lower()
    meses_tabela = [l.split("|")[1].strip() for l in nota.split("## Projeção")[1].splitlines() if l.startswith("| ") and "/" in l.split("|")[1]]
    assert len(meses_tabela) == len(set(meses_tabela)) == 6
