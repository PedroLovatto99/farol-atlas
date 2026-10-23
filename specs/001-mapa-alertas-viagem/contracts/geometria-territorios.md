# Contrato do arquivo de geometria

Arquivo estático `frontend/public/geo/territorios.geojson`, gerado por `backend/scripts/gerar_geometria.py` (derivado de `prototipos/mapa/montar_dados.py`) só quando as regras de território mudam. Versionado no repositório. O frontend o busca uma vez; o nível de cada feição vem de `GET /mapa`, pelo `codigo`.

## Origem

Natural Earth 10m, países, versão "ponto de vista do Brasil" (`ne_10m_admin_0_countries_bra`), simplificada com mapshaper na precisão `0.0005` (para o Vaticano não sumir). O pré-processamento que cria as propriedades `nome`, `iso` e `soberano` consumidas pelo script deve ser descrito no README do script.

## Propriedades de cada feição

| Propriedade | Tipo | Significado |
|---|---|---|
| `codigo` | string | Código próprio do território (igual a `territorio.codigo`). Para neutro: o código original, só para depuração. |
| `soberano` | string \| null | País soberano (dependências, Kosovo→`RS`, Malvinas→`AR`). |
| `tipo` | `pais` \| `dependencia` \| `neutro` | Neutro não responde a toque nem tem nível (FR-016, FR-032). |
| `titulo` | string | Nome exibido; dependência como "Nome (País)". |
| `zoom` | string | Grupo de enquadramento (feições com o mesmo `zoom` formam a caixa; usa-se a maior parte do território). |

## Regras aplicadas pelo script (spec, "Regras do mapa")

| Regra | Requisito |
|---|---|
| 198 países do Itamaraty selecionáveis, incluindo o Brasil | FR-029 |
| Kosovo desenhado como parte da Sérvia, com observação | FR-030 |
| Dependências apontam para o soberano e usam a própria bandeira | FR-031 |
| Guiana Francesa separada da França (recorte geográfico) | FR-031 |
| Antártida, Saara Ocidental e áreas sem soberania reconhecida: `neutro` | FR-032 |
| Taiwan como dependência da China, sem bandeira | FR-033 |
| Malvinas como parte da Argentina, com observação (hoje o script as trata como neutras: **mudar**) | FR-034 |
| Ilhas que dividem o código com o país (Clipperton/FR, ilhas australianas/AU) viram dependência à parte | protótipo |

## Testes do arquivo

1. Os 198 países do Itamaraty têm ao menos uma feição `tipo = pais` com o seu `codigo`.
2. Nenhuma feição `tipo = pais` ou `dependencia` tem `codigo` fora de `territorio` (seed), e vice-versa.
3. Todo `soberano` existe e é `pais`.
4. `FK` não é `neutro`; `EH`, `AQ` são.
5. O arquivo tem tamanho abaixo de um limite fixado na primeira geração (regressão de simplificação).
