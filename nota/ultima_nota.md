# Monitor de inflação: IPCA de set/26

*Atualizado automaticamente após a divulgação do IPCA pelo IBGE.*

## Destaques

- **IPCA de set/26: 0,82%.** A mediana do Focus coletada no meio do mês esperava 0,50%: surpresa de 0,32 p.p.
- **Acumulado em 12 meses: 4,58%**, para uma meta de 3,0% e teto de 4,5% (acima do teto).
- **Acumulado no ano: 3,95%.**
- **Inflação projetada para os próximos 12 meses (SARIMA, até set/27): 5,97%.**

## Leitura

*Leitura referente ao IPCA de agosto de 2026.*

A deflação de 0,32% em agosto veio de preços administrados e de alimentos, e não de uma desaceleração mais ampla. Habitação foi o principal vetor, com contribuição de −0,29 p.p.: a energia elétrica caiu 7,63% com o Bônus de Itaipu creditado nas faturas do mês. Transportes contribuiu com −0,17 p.p., com a queda das passagens aéreas e dos combustíveis, e Alimentação e bebidas com −0,07 p.p., com a queda dos alimentos in natura. No sentido contrário, Despesas pessoais somou +0,13 p.p., quase tudo pelo reajuste do cigarro.

O resultado ficou abaixo da mediana do Focus coletada no meio do mês, e o acumulado em 12 meses recuou para 4,22%, consolidando o retorno ao intervalo de tolerância da meta depois de ter ficado acima do teto de 4,5% em junho. A melhora, porém, depende em boa parte de um fator que não se repete: o bônus é um crédito pontual, e a tarifa de energia volta ao nível anterior nas faturas seguintes.

Essa é a principal razão da distância entre as projeções para setembro: o SARIMA espera 0,09% e o Focus, 0,56%. O modelo é univariado e lê a deflação de agosto como informação sobre a tendência; o mercado incorpora a reversão do bônus. O caso ilustra o limite do modelo puramente estatístico em meses dominados por preços administrados e reforça o próximo passo do projeto: incluir variáveis de fora da série, como o IPCA-15 e o calendário de reajustes.

*Fonte dos itens: IBGE, divulgação do IPCA de agosto de 2026.*

## Contribuições por grupo

| Grupo | set/26 (p.p.) | Soma dos últimos 12 meses (p.p.) |
|---|---:|---:|
| Alimentação e bebidas | 0,18 | 0,98 |
| Habitação | 0,35 | 0,64 |
| Transportes | 0,18 | 0,79 |
| Saúde e cuidados pessoais | 0,01 | 0,76 |
| Demais grupos | 0,10 | 1,30 |

![Contribuições](../output/figuras/contribuicoes.png)

## Projeção

| Mês | SARIMA (%) | Intervalo de 80% | Focus, mediana (%) | Acumulado em 12 meses, SARIMA (%) |
|---|---:|---:|---:|---:|
| out/26 | 0,64 | 0,30 a 0,99 | 0,32 | 5,15 |
| nov/26 | 0,55 | 0,17 a 0,93 | 0,35 | 5,54 |
| dez/26 | 0,62 | 0,23 a 1,02 | 0,56 | 5,85 |
| jan/27 | 0,49 | 0,09 a 0,89 | 0,45 | 6,02 |
| fev/27 | 0,67 | 0,27 a 1,07 | 0,66 | 5,98 |
| mar/27 | 0,58 | 0,18 a 0,99 | 0,41 | 5,67 |

![Projeção](../output/figuras/projecao.png)

### Desempenho fora da amostra

Previsões um passo à frente nos últimos 36 meses, em pontos percentuais. A mediana do Focus é a coletada na metade do mês de referência, quando o IPCA do mês anterior já é conhecido, o mesmo conjunto de informação dos modelos.

| Modelo | RMSE | MAE | Viés |
|---|---:|---:|---:|
| Mediana do Focus | 0,155 | 0,117 | -0,021 |
| Sazonal simples | 0,263 | 0,212 | -0,015 |
| SARIMA | 0,304 | 0,223 | 0,022 |

![IPCA em 12 meses](../output/figuras/acumulado_12m.png)
