# Monitor de inflação: IPCA de ago/26

*Atualizado automaticamente após a divulgação do IPCA pelo IBGE.*

## Destaques

- **IPCA de ago/26: -0,32%.** A mediana do Focus coletada no meio do mês esperava -0,17%: surpresa de -0,15 p.p.
- **Acumulado em 12 meses: 4,22%**, para uma meta de 3,0% e teto de 4,5%.
- **Acumulado no ano: 3,11%.**
- **Inflação projetada para os próximos 12 meses (SARIMA, até ago/27): 4,59%.**

## Contribuições por grupo

| Grupo | ago/26 (p.p.) | Soma dos últimos 12 meses (p.p.) |
|---|---:|---:|
| Alimentação e bebidas | -0,07 | 0,74 |
| Habitação | -0,29 | 0,74 |
| Transportes | -0,17 | 0,62 |
| Saúde e cuidados pessoais | 0,03 | 0,78 |
| Demais grupos | 0,19 | 1,26 |

![Contribuições](../output/figuras/contribuicoes.png)

## Projeção

| Mês | SARIMA (%) | Intervalo de 80% | Focus, mediana (%) | Acumulado em 12 meses, SARIMA (%) |
|---|---:|---:|---:|---:|
| set/26 | 0,09 | -0,25 a 0,43 | 0,56 | 3,82 |
| out/26 | 0,28 | -0,10 a 0,66 | 0,33 | 4,01 |
| nov/26 | 0,32 | -0,07 a 0,72 | 0,35 | 4,16 |
| dez/26 | 0,48 | 0,08 a 0,88 | 0,56 | 4,32 |
| jan/27 | 0,41 | 0,00 a 0,81 | 0,46 | 4,39 |
| fev/27 | 0,60 | 0,20 a 1,01 | 0,66 | 4,29 |

![Projeção](../output/figuras/projecao.png)

### Desempenho fora da amostra

Previsões um passo à frente nos últimos 36 meses, em pontos percentuais. A mediana do Focus é a coletada na metade do mês de referência, quando o IPCA do mês anterior já é conhecido, o mesmo conjunto de informação dos modelos.

| Modelo | RMSE | MAE | Viés |
|---|---:|---:|---:|
| Mediana do Focus | 0,147 | 0,112 | -0,009 |
| Sazonal simples | 0,246 | 0,198 | 0,001 |
| SARIMA | 0,279 | 0,205 | 0,045 |

![IPCA em 12 meses](../output/figuras/acumulado_12m.png)
