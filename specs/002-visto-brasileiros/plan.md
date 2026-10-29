# Implementation Plan: Requisitos de visto para brasileiros, por país

**Branch**: `002-visto-brasileiros` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-visto-brasileiros/spec.md`

> **Aprovado em 28/10/2026:** o levantamento obrigatório (`research.md`, seção 3) e as decisões O1 a O12 (`research.md`, seção 4). O **conteúdo** dos dicionários de rótulos, de nomes e de regras por país é escrito na implementação, de acordo com o que foi aprovado, e cada entrada leva um teste.

## Summary

O painel de cada país ganha a seção "Visto" e o globo pode ser pintado por visto. Um módulo novo do backend, `vistos`, lê **uma vez por semana** a página do artigo "Visa requirements for Brazilian citizens" da Wikipédia (sem usar a API, que o `robots.txt` proíbe), liga cada linha a um território do mapa por um dicionário de nomes, traduz as observações em lote com um LLM configurável, e **só substitui o que o site mostra se a coleta for válida** (formato esperado e países reconhecidos ≥ 90% da coleta anterior, ou ≥ 150 na primeira). Mudanças para uma categoria **menos exigente** (ou passar a aceitar só o RG) ficam **retidas por país** até o dono confirmar. A `api` junta o painel (do `mapa`) e o visto (do `vistos`), e expõe `GET /vistos` para o globo. O frontend ganha o seletor "Alertas | Vistos" (padrão "Alertas", não lembrado), a paleta e a legenda de vistos com o subitem "Isento, entrada com RG" (listras no MapLibre) e a linha de fonte e data, visível mesmo com a legenda recolhida. O painel do país ganha o botão **recolher** (FR-030), para o globo ficar visível com um país selecionado: uma barra horizontal compacta, a mesma nos dois formatos (flutuando no lugar do painel no computador; no rodapé no celular).

Detalhes: [research.md](research.md) (conferências, levantamento da fixture e decisões), [data-model.md](data-model.md), [contracts/](contracts/) e [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.13 (backend e worker); TypeScript com `strict: true` (frontend). Igual à 001.

**Primary Dependencies**: as da 001. **Nenhuma dependência nova**, no backend nem no frontend: o parser usa BeautifulSoup4 (já em uso), a checagem de `robots.txt` usa protego, a tradução usa LangChain 1.x (`init_chat_model`, `with_structured_output`) e o padrão do globo é uma matriz de pixels gerada no código. `pycountry` e `shapely` continuam só no grupo de desenvolvimento.

**Storage**: PostgreSQL 18, migração Alembic `0003_vistos` (4 tabelas novas; nenhuma da 001 muda). Dicionários em YAML dentro do pacote.

**Testing**: pytest (PostgreSQL de teste; fixture real da Wikipédia; sessão HTTP falsa; tradutor falso) e Vitest + Testing Library (API simulada; mapa substituído por um falso). Mesmas pastas que o CI já roda (`tests/unidade`, `tests/contrato`, `tests/integracao`).

**Target Platform**: Docker Compose, como na 001.

**Project Type**: web-service + web-application, com o worker agendado na mesma imagem.

**Performance Goals**: `GET /vistos` com número fixo de consultas (3); o visto do painel com número fixo (3 a mais que a 001); a coleta tem 2 requisições à Wikipédia por tentativa (a página e o `robots.txt`) e leva segundos, mais ~8 chamadas ao LLM na primeira coleta.

**Constraints**: 360 px de largura; sem requisição por país no carregamento (o `/vistos` é sob demanda, ao entrar no modo "Vistos"); texto da fonte sempre tratado como dado; operação gratuita (Gemini no plano gratuito ou Ollama local; a falha do LLM não impede a coleta).

**Scale/Scope**: cerca de 230 registros de visto, uma coleta por semana, poucos pendentes para o dono.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Resultado | Como o plano atende |
|---|---|---|
| I. Qualidade por ferramenta | Passa | Ruff, mypy `strict`, ESLint e `tsc` `strict` valem para o código novo; nada de `any`. Tudo precisa passar em `uv run poe verificar` e `npm run verificar`, que o CI da `main` já roda sem segredos. |
| II. TDD | Passa | Cada regra (normalização, dicionário, rótulos combinados, RG, permanência, validade, estabilidade, retenção, tradução, leitura) tem teste antes do código; as tarefas ficam nessa ordem. Sem rede e sem LLM de verdade (tradutor falso; fixture). Na interface, comportamento, não aparência. |
| III. Arquitetura | Passa (constituição **v1.0.3**, emendada em 28/10/2026) | `vistos` é módulo novo na camada de `mapa`, `coleta` e `classificacao`, sem importar nem ser importado por eles; o que é comum (cliente HTTP educado, relógio, parâmetros de modelo) sobe para a `infra` (D1). Modelos e repositórios no `dominio`; contratos do import-linter atualizados (8). Rotas só convertem; a junção painel+visto é uma função de composição da `api`, sem regra de negócio. DTOs Pydantic; tipos do frontend gerados do OpenAPI. Sem N+1, com teste de limite de consultas em `/vistos`. Frontend por funcionalidade; mapa atrás de `MapaProps`. **Carregamento do mapa:** `/mapa` continua sendo a única chamada do carregamento inicial; `/vistos` só é pedida quando a pessoa escolhe o modo "Vistos", o que a v1.0.3 permite (dados de modo opcional sob demanda, desde que o carregamento inicial não dependa deles; O10). **Rota de país:** chama dois módulos por intermédio da `api`; isso não cria dependência entre `mapa` e `vistos`. |
| IV. Coleta responsável | Passa, depois de **um conserto** | `robots.txt` por protego antes da requisição; sem API da Wikipédia; User-Agent no formato da Wikimedia com o repositório como contato; pausa de 2 s; parada em 403, 429 ou verificação humana. **Achado:** o detector de verificação humana da 001 confundiria a página da Wikipédia com um CAPTCHA (a palavra aparece em um `<script>` de configuração) e a coleta pararia; o conserto (ignorar `<script>` e `<style>`) vem com teste que usa a fixture. Regra de estabilidade e limite de tentativas evitam insistir. |
| V. Informação confiável | Passa | Sem dado ⇒ "Sem informação de visto", nunca uma categoria deduzida; rótulo desconhecido ou parte "Outra situação" ⇒ "Outra situação" com o rótulo à vista, nunca a mais favorável; mudança para menos exigente fica retida; toda informação mostra fonte, data **do dado de cada país** e o aviso de site não oficial, no painel e no mapa (linha de fonte no modo Vistos); tradução marcada como automática e com o original à mão. |
| VI. Acessível e celular | Passa | Categoria sempre também em texto; o "Isento com RG" se distingue por **listras e por texto** (não só cor); estado misto da legenda por `aria-checked="mixed"` e "(parcial)"; contraste verificado (paleta abaixo); 360 px com a linha de fonte visível; sem animação nova (respeita `prefers-reduced-motion`). |
| VII. Simples e gratuito | Passa | Nada novo na infraestrutura; LLM configurável por `LLM_TRADUTOR` (Gemini gratuito ou Ollama); sem o LLM a coleta segue e as observações aparecem em inglês. |
| VIII. Segurança | Passa | Rotas novas só de leitura; nenhuma de escrita (o dono usa comandos dentro do contêiner do worker); texto da Wikipédia e tradução tratados como dados (texto puro no banco e na API, sem HTML; o React escapa; no prompt vão entre delimitadores e a saída é validada pelo Pydantic com tamanho limitado); segredos só em variáveis de ambiente; entradas validadas; `pip-audit` e `npm audit` continuam nos comandos de verificação (sem dependência nova). |
| Idioma | Passa | Interface, documentação, nomes e comentários em português. |

**Re-checagem após o desenho (Fase 1):** sem violações. Esta checagem usa a constituição v1.0.3.

## Project Structure

### Documentation (this feature)

```text
specs/002-visto-brasileiros/
├── plan.md              # Este arquivo
├── research.md          # Fase 0: conferências, levantamento da fixture, decisões e riscos
├── data-model.md        # Fase 1: tabelas, estados, retenção
├── quickstart.md        # Fase 1: como validar
├── contracts/
│   ├── openapi.yaml             # API v1.1 COMPLETA (substitui o da 001 nos testes de contrato)
│   ├── dicionario-de-rotulos.md # Formato dos dicionários (conteúdo aprovado no levantamento; escrito na implementação)
│   ├── comandos-do-dono.md      # Comandos, saídas, códigos de saída, log e agenda
│   └── mapa-props-vistos.md     # Mudanças em MapaProps, camadas, legenda e estado
├── checklists/requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/0003_vistos.py                  # novo
├── src/farol/
│   ├── infra/
│   │   ├── cliente_http.py        # novo (movido de coleta): ClienteEducado, Pagina, SessaoHttp, RespostaHttp,
│   │   │                          #   Baixador, parece_verificacao (ignora <script>/<style>); User-Agent novo
│   │   ├── modelo.py              # novo: argumentos_do_modelo(nome, configuracoes) (sem importar LangChain)
│   │   └── config.py              # + llm_tradutor
│   ├── dominio/
│   │   ├── enums.py               # + CategoriaDeVisto e demais enums
│   │   ├── modelos.py             # + ColetaVistos, RequisitoVisto, MudancaRetida, ItemParaRevisao
│   │   ├── constantes.py          # novo: CODIGO_DO_BRASIL (hoje local de mapa/painel.py)
│   │   └── repositorios/vistos.py # novo: repositórios de vistos
│   ├── coleta/                    # passa a importar o cliente HTTP da infra
│   ├── classificacao/cadeia.py    # usa infra.argumentos_do_modelo
│   ├── vistos/                    # NOVO módulo (interface pública: __init__.py)
│   │   ├── fonte.py               # URL, nome, licença; extração da página (tabelas, JSON-LD) → linhas
│   │   ├── normalizacao.py        # normalização de texto
│   │   ├── dicionario.py          # carrega e valida rotulos/nomes/regras; classificar_rotulo, ligar_nome
│   │   ├── dicionarios_yaml/      # rotulos.yaml, nomes.yaml, regras_por_pais.yaml (com hash_observacao)
│   │   ├── permanencia.py         # formatos conhecidos (FR-004a)
│   │   ├── consolidacao.py        # linhas → candidato por território (combinados, hash)
│   │   ├── retencao.py            # decidir_retencao (função pura) e estados
│   │   ├── validade.py            # critérios da coleta válida
│   │   ├── estabilidade.py        # adiar se a edição tem menos de 24 h; 3 adiamentos
│   │   ├── tradutor.py            # Protocol Tradutor + saída estruturada (Pydantic)
│   │   ├── tradutor_langchain.py  # adaptador (init_chat_model + with_structured_output)
│   │   ├── servico_coleta.py      # ServicoDeColetaDeVistos
│   │   ├── servico_dono.py        # listar pendentes, confirmar, rejeitar, ignorar nome
│   │   ├── leitura.py             # montar_visto_do_pais, montar_vistos_do_mapa
│   │   └── visoes.py              # dataclasses imutáveis devolvidas à api
│   ├── mapa/painel.py             # importa CODIGO_DO_BRASIL do dominio
│   ├── api/
│   │   ├── composicao.py          # novo: painel + visto
│   │   ├── dtos.py                # + Visto, VistosDoMapa e apoio
│   │   ├── rotas/vistos.py        # novo: GET /vistos
│   │   └── rotas/paises.py        # + visto (composição)
│   └── worker/
│       ├── agenda.py              # + job semanal, partida e "amanhã" (vistos)
│       ├── comando.py             # + coletar --vistos e o grupo "vistos"
│       └── jobs.py                # + rodada_real_de_vistos
└── tests/
    ├── fixtures/wikipedia/        # página real + README.md (feito)
    ├── unidade/vistos/            # parser, normalização, dicionários, combinados, RG, permanência, validade,
    │                              #   estabilidade, retenção, tradutor
    ├── unidade/worker/            # comandos e agenda de vistos (junto dos testes da 001)
    ├── unidade/infra/             # cliente HTTP (movido), "captcha" na fixture, User-Agent
    ├── integracao/vistos/         # repositórios, migração, serviço de coleta (retenção), leitura, comandos
    ├── integracao/api/            # /vistos e paises.visto
    └── contrato/                  # aponta para o contrato da 002

frontend/
├── scripts/gerar-tipos.mjs        # contrato padrão passa a ser o da 002
└── src/
    ├── servicos/api/              # esquema.d.ts regerado; cliente: Visto, VistosDoMapa, obterVistos
    ├── estado/reducer.ts          # + modo, vistosMarcados, painelRecolhido e ações
    ├── compartilhado/vistos.ts    # categorias, rótulos, textos, cores, ordem e chaves da legenda
    └── funcionalidades/
        ├── vistos/                # SecaoVisto, SeletorDeModo, LegendaDeVistos, LinhaDaFonteDeVistos, useVistos
        ├── legenda/               # + filtroDeVistos.ts (puro) e troca da legenda por modo
        ├── mapa/                  # tipos (Preenchimento), cor/feicoes, padroes.ts, adaptador (camada padrao-rg)
        ├── painel/Painel.tsx      # + SecaoVisto; + botão "Recolher painel" (FR-030)
        ├── painel/BarraDoPainel.tsx # novo: o painel recolhido (barra horizontal única, flutuante no desktop e no rodapé no celular)
        └── aviso/Aviso.tsx        # + aviso de vistos desatualizados no modo Vistos

.env.example                       # + LLM_TRADUTOR; CONTATO_COLETA com o repositório
```

**Structure Decision**: a mesma aplicação web da 001 (`backend/` e `frontend/`). `vistos` é um módulo de domínio novo no backend, no nível de `mapa`, `coleta` e `classificacao`; o cliente HTTP educado, hoje dentro de `coleta`, sobe para a `infra` porque dois módulos o usam.

### Nomes reais reaproveitados (lidos no código e na configuração, nada inventado)

| O quê | Nome real |
|---|---|
| Tarefas do poe | `lint`, `formato`, `tipos`, `arquitetura`, `testes`, `auditoria`, `verificar`, `exportar-openapi` (**nenhuma nova**) |
| Scripts do npm | `lint`, `formato`, `tipos`, `testes`, `build`, `auditoria`, `verificar`, `gerar-tipos` (**nenhum novo**) |
| Variáveis de ambiente | `CONTATO_COLETA`, `PAUSA_SEGUNDOS`, `LLM_CLASSIFICADOR`, `GOOGLE_API_KEY`, `OLLAMA_BASE_URL`, `DATABASE_URL`, `DATABASE_URL_TESTE`, `DIRETORIO_DADOS`, `API_DOCS_HABILITADA`, `CORS_ORIGENS`. **Nova:** `LLM_TRADUTOR` |
| Comandos do worker | `python -m farol.worker`, `coletar --alertas`, `coletar --postos`, `reclassificar <id\|url>`. **Novos:** `coletar --vistos` e `vistos pendentes\|confirmar\|rejeitar\|ignorar-nome` |
| Serviços do Compose | `postgres`, `postgres-teste` (perfil `teste`), `migracao`, `api`, `worker`, `frontend` |
| Jobs do APScheduler | `alertas-diarios`, `alertas-na-partida`, `postos-mensais`, `postos-na-partida`. **Novos:** `vistos-semanais`, `vistos-na-partida`, `vistos-amanha` |
| CI | `ci.yml` roda `uv run poe lint\|formato\|tipos\|arquitetura`, `pytest tests/unidade tests/contrato`, `pytest tests/integracao`; `npm run lint\|formato\|tipos\|testes\|build`. As pastas novas de testes entram sozinhas |
| Operações no cliente | `User-Agent`: `FarolAtlas/0.1 (<contato>; projeto pessoal) python-requests/<versão>` (novo formato) |

## Paleta do modo "Vistos"

Escolhida pelo responsável (29/10/2026, opção A: amarelo → roxo; **mais escuro = mais exigente**) e **conferida por script** (contraste WCAG 2.x e distância de cor CIEDE2000, em visão normal e com simulação de protanopia, deuteranopia e tritanopia). A paleta de partida (`#F5D547`, `#F29CC3`, `#9A6BD8`, `#3B1C6B`, `#8C8070`, `#C8C4BB`) falhava em vários pares; os ajustes abaixo mexeram **só na luminosidade (L* do CIELAB), mantendo o matiz** (e a croma, reduzida apenas onde saía do gamute sRGB). Os tokens estão em `tema.css` (`--color-visto-*`), com o hex repetido em `compartilhado/vistos.ts` (um teste confere que são iguais, como na 001).

| Chave | Cor | Ajuste (L*) | Contra branco (legenda) | Contra o oceano `#DCE8F2` | Contra o contorno branco |
|---|---|---|---|---|---|
| Isento de visto | `#FEDD50` | de `#F5D547`, 85,7 → 88,6 | 1,34 | 1,08 | 1,34 |
| Isento, entrada com RG | `#FEDD50` + listras `#1F2A44` | listras como pedido | — | — | listras 10,64:1 sobre a base (mínimo 3:1) |
| Visto na chegada | `#D17DA4` | de `#F29CC3`, 73,9 → 62,4 | 2,92 | 2,35 | 2,92 |
| Autorização ou visto eletrônico | `#8F5FCC` | de `#9A6BD8`, 54,4 → 50,0 | 4,49 | 3,61 | 4,49 |
| Visto exigido | `#3B1C6B` | sem ajuste | 13,42 | 10,78 | 13,42 |
| Outra situação | `#948878` | de `#8C8070`, 54,2 → 57,3 | 3,47 | 2,79 | 3,47 |
| Sem informação de visto | `#BEBAB1` | de `#C8C4BB`, 79,2 → 75,6 | 1,94 | 1,55 | 1,94 |
| Brasil (neutro) | `#F1EFE8` | sem ajuste | — | — | — |

O contorno do globo é a linha branca de 0,6 px da camada `fronteiras` (`#FFFFFF`; 1,24:1 contra o oceano), por isso a última coluna é o mesmo contraste da coluna do branco.

**Distância de cor (CIEDE2000), menor valor em cada visão:**

| Visão | Cores que aparecem juntas no globo (entre si, com o Brasil e com o oceano) | Cor de visto contra as de alerta (salvo as exceções abaixo) |
|---|---|---|
| Normal | 12,45 (sem informação × Brasil) | 20,03 |
| Protanopia | 12,61 (sem informação × Brasil) | 13,07 (outra situação × não viajar) |
| Deuteranopia | 12,15 (visto na chegada × sem informação) | 13,25 (outra situação × não viajar) |
| Tritanopia | 12,64 (sem informação × Brasil) | 14,47 (isento × não verificado) |

Critério adotado: **≥ 12** entre todas as cores que aparecem juntas no globo. Contra as cores de alerta, que pertencem ao outro modo e **nunca aparecem no mesmo globo**, também ≥ 12, com as três exceções abaixo, que **não** chegam a 12 só com ajuste de luminosidade:

| Par (visto × alerta) | Normal | Protanopia | Deuteranopia | Tritanopia |
|---|---|---|---|---|
| Isento (amarelo) × evite (âmbar `#FAC775`) | 11,15 | 8,39 | 6,55 | 5,96 |
| Isento × sem alerta (verde `#C0DD97`) | 19,29 | 11,64 | 12,52 | 29,17 |
| Sem informação × não verificado (`#D3D1C7`) | 5,79 | 5,62 | 5,60 | 5,81 |

- **Amarelo contra âmbar.** São dois amarelos claros: com o matiz mantido, não há luminosidade do amarelo que o afaste do âmbar em 12 nas quatro visões sem esbarrar no Brasil (mais claro) ou no verde, no roxo e no marrom da própria paleta (mais escuro). O ponto escolhido (`#FEDD50`) é o que mais afasta o par sem quebrar as outras. Como os modos não aparecem juntos no globo e o "Isento" tem sempre o texto da legenda ao lado, o par tem limite próprio de **5,5** (teste `vistos.test.ts`); se for preciso 12, o amarelo precisa mudar de **matiz**, o que depende de decisão do responsável.
- **Sem informação × não verificado.** Os dois são "nada confirmado", em modos diferentes, e nunca aparecem juntos. Com o cinza novo o par mede **5,6 a 5,8** (antes, com `#AEABA2`, 9,9). O tratamento à parte segue aceito; o valor real é o da tabela acima.
- **Amostras da legenda:** borda de 1 px em `#5F5E5A` (6,5:1 contra o branco; WCAG 1.4.11), porque o "Isento" (1,3), o "Visto na chegada" (2,9) e o "Sem informação" (1,9) ficam abaixo de 3:1 contra o fundo branco. A legenda inclui o texto de cada categoria, então a cor nunca é a única informação.
- **Contraste de objeto gráfico (WCAG 1.4.11) no globo: NÃO atendido pelo contorno.** O contorno é branco de 0,6 px (1,24:1 contra o oceano; entre 1,34 e 13,42 contra as cores de visto, só o "Visto exigido", a "Autorização" e a "Outra situação" passam de 3:1). Portanto o critério **não** é atendido pelo contorno e fica registrado como pendente: as opções estão no relatório de 29/10/2026 e nenhuma mudança no globo foi feita. A informação da categoria também está no painel do país, na legenda em texto e no nome acessível, mas isso não cumpre sozinho o 1.4.11 para o objeto gráfico.
- O "sem informação" **muda de tom** entre os modos (no modo Alertas, "não verificado" segue `#D3D1C7`): tem outro significado e precisa se distinguir do neutro do Brasil, que no modo Alertas não existe como estado.
- Verificação permanente: um teste do frontend recalcula o contraste das listras (≥ 3) e as distâncias mínimas (com as matrizes de daltonismo) a partir de `compartilhado/vistos.ts` e `niveis.ts`. A tabela acima é o resultado do script de dimensionamento; os limites e as exceções estão no teste.

## Painel recolhível (FR-030)

Pedido de 29/10/2026: o modo "Vistos" precisa do mapa visível com um país selecionado. Só frontend; nenhuma dependência nova, nenhuma rota nova.

**Como o "Ver mundo" funciona hoje (001).** O botão está no cabeçalho do painel (`Painel.tsx`) e chama `verMundo` em `App.tsx`: despacha `limpar-selecao` (zera `selecionado`, `postosExpandidos` e `grupoEmDestaque`) e pede a câmera `{ tipo: "mundo" }`. Sem `selecionado`, o `usePais` volta a `ocioso` e o painel **sai da tela**. Esc faz o mesmo (se não houver diálogo aberto), e o toque no oceano também limpa a seleção, mas sem mexer na câmera. Ou seja, "Ver mundo" **fecha** e **desseleciona**; o recolher é outra coisa.

**Como os dois convivem.**

| | Recolher | Ver mundo |
|---|---|---|
| País selecionado | continua | deixa de estar |
| Câmera | não muda | volta ao mundo |
| Postos expandidos e destaque | ficam | são zerados |
| Painel | vira barra | sai da tela |
| Volta | tocar na barra | selecionar de novo (abre expandido) |

A barra recolhida **também tem o "Ver mundo"** (segundo botão, só ícone com nome acessível), para o painel nunca ficar sem saída enquanto o país está selecionado; Esc continua valendo. Fechar zera o recolhido (não há `selecionado`).

**Estado.** `painelRecolhido: boolean` no `reducer.ts`, padrão `false`, nunca gravado (nem `localStorage`). Ações `recolher-painel` e `expandir-painel`. `selecionar`, `tocar-icone` e `limpar-selecao` voltam a `false`; `expandir-posto` também (um posto expandido precisa do painel aberto). Trocar o modo e mexer na legenda não mudam o campo. O botão só existe com o país carregado (`pronto`); em "carregando" e "erro" o painel fica expandido.

**Componentes.**
- `Painel.tsx` recebe `recolhido` e `onAlternarRecolhimento`; no cabeçalho, ao lado do "Ver mundo", o botão "Recolher painel" (`aria-expanded="true"`, ícone de seta). Recolhido, o `Painel` renderiza a `BarraDoPainel` no lugar do `aside` expandido (o conteúdo sai do DOM; os postos abertos são do reducer e voltam sozinhos).
- `BarraDoPainel.tsx` (novo): um `<aside aria-label="Detalhes do país (recolhido)">` com um botão principal que ocupa a barra (bandeira, nome, situação; nome acessível "Expandir painel: <nome>, <situação>"; `aria-expanded="false"`) e o "Ver mundo". **Um componente só, texto sempre na horizontal**: bandeira, bloco de texto (nome em cima, situação embaixo), botão de expandir e "Ver mundo", com altura mínima de 56 px. O nome quebra em até duas linhas (`line-clamp-2`, `break-words`) e a situação nunca é cortada. **Computador** (`modo="lateral"`): flutua na posição do painel, `absolute right-2 top-16 z-20 w-[340px]` (a mesma largura e o mesmo canto do painel; o "Sobre" no topo continua livre). **Celular** (`modo="gaveta"`): `absolute inset-x-2 bottom-2 z-20`, em largura total.
- A situação principal vem de dados que o painel já carregou: `NIVEIS[pais.nivel].rotulo` (ou `ALERTA_SO_REGIONAL.rotulo`, como o `NivelDoPais`) no modo "Alertas"; `ROTULOS_DE_VISTO[pais.visto.situacao]` no modo "Vistos" (Kosovo e Malvinas: "Kosovo: Isento de visto", com `territorio_nome`). **Não depende** de `GET /vistos`. Brasil: `visto = null` e nenhuma situação, só bandeira e nome.
- O foco vai, depois da troca, ao botão que passa a valer (`Expandir painel` na barra; `Recolher painel` no cabeçalho), com o mesmo cuidado do foco já existente no `Painel`.

**Layout e câmera.**
- A câmera **não se move** ao recolher ou expandir. O enquadramento continua sendo feito ao selecionar, com `margemDoLayout` do painel expandido; recolhido, o país fica descentrado dentro de uma área visível maior, o que é aceitável e evita animação inesperada. Se isso incomodar na medição (T126), um pedido `garantir-visivel` ao recolher é o ajuste, mas **não** entra por padrão.
- `App.tsx` passa `data-painel-recolhido` junto de `data-painel-aberto` e `data-modo-do-painel`. O CSS de `tema.css` (que hoje afasta os controles de zoom do painel: 352 px à direita no lateral, 55dvh embaixo na gaveta) ganha o caso recolhido: no **computador** nenhum deslocamento (a barra fica no canto superior direito e os controles de zoom ficam livres no canto inferior direito); no **celular**, os controles sobem para ~72 px do rodapé, acima da barra.
- **Celular: legenda e linha de fonte** ficam em `bottom-10` e hoje são cobertas pela gaveta de 55dvh. Com a barra (56 px ou mais, mais a margem) no rodapé elas **não podem ficar por baixo dela**: com `data-painel-recolhido="true"` no celular, sobem para acima da barra (variável CSS `--rodape-ocupado`). Isso entra nos testes do `App` e na medição em 360 px.
- Transição: nenhuma animação nova por padrão; se houver (fade curto da barra), fica dentro de `prefers-reduced-motion` (`motion-reduce:transition-none`), como o resto, com teste.

**Constituição.** VI (acessível e celular): botão com nome e `aria-expanded`, teclado, 360 px, alvo ≥ 44 px, sem gesto de arrastar, sem animação obrigatória. III: só estado de interface no reducer; nada no `mapa`. Nenhum princípio muda.

## Ordem de entrega sugerida (insumo para /speckit-tasks)

As tarefas ficam agrupadas por história. **A P1 inteira (backend + painel) entrega valor e é testável antes de começar a P2.**

0. **Fundamentos (sem mudar comportamento)**, com tudo verde ao fim:
   - mover `ClienteEducado`/`Pagina`/`SessaoHttp`/`RespostaHttp`/`Baixador`/`parece_verificacao` para a `infra`, com os testes da 001 junto (**só os imports mudam**); corrigir o "captcha" descartando só o texto inline de `<script>`/`<style>` (atributos e texto visível continuam examinados), com dois testes novos: desafio real (iframe e div de captcha visíveis) **continua detectado** e a fixture da Wikipédia **não é** detectada; trocar o User-Agent;
   - `argumentos_do_modelo` na `infra`; `CODIGO_DO_BRASIL` no `dominio`;
   - contratos do import-linter para o módulo `vistos` (8 contratos); `.env.example`; `LLM_TRADUTOR`.
1. **Portão de aprovação: CUMPRIDO em 28/10/2026** (O1 a O4 aprovados). O conteúdo dos três dicionários pode ser escrito conforme `research.md` 3.1 a 3.5. Um ponto segue aberto para conferência, sem bloquear: a parte `online visa` do combinado `Online Visa / Visa on arrival` (Burundi, Nepal) como Autorização ou visto eletrônico (`research.md` 3.1).
2. **Dados:** enums, modelos ORM, migração `0003`, repositórios, com testes de integração (migração sobe e desce).
3. **P1, backend:**
   1. parser da fixture (JSON-LD, tabelas, linhas) e normalização;
   2. dicionários e ligação de nomes, com um teste por entrada (inclui a regra geral de categoria da O1 e o `hash_observacao` das regras por país, com a lista de revisão);
   3. consolidação (combinados, duplicatas, hash), permanência, RG;
   4. validade, estabilidade e **retenção** (funções puras, testadas em tabela);
   5. tradutor (Protocol, saída estruturada, adaptador, falso) e tradução em lote;
   6. serviço de coleta (persistência, itens não reconhecidos, resolução automática) e serviço do dono;
   7. leitura (`montar_visto_do_pais`, `montar_vistos_do_mapa`), dependências, Kosovo e Malvinas, Brasil;
   8. API: DTOs, `GET /vistos`, `visto` em `Pais`, contrato completo, teste de contrato apontando para a 002, **teste que trava a parte da 001** (`test_contrato_002_preserva_001.py`: falha se rota, parâmetro, resposta, esquema ou propriedade da 001 mudar ou sumir; única adição permitida: `Pais.visto`), teste de limite de consultas;
   9. worker: comandos, agenda (semanal, partida, amanhã), jobs, log de pendências;
   10. teste de ponta a ponta com a fixture inteira (no estilo do teste do Líbano da 001): 100% de cobertura de ligação, nenhum rótulo desconhecido, Argentina com RG, Jamaica "varia", Guernsey no Reino Unido, Brasil sem seção.
4. **P1, frontend:** regenerar os tipos; cliente e validação; `SecaoVisto` (todos os estados da spec); `Painel`; textos fixos (aviso, fonte CC BY-SA); testes de comportamento.
5. **Ponto de controle da P1:** `uv run poe verificar` e `npm run verificar`; passos 1 a 8 do quickstart; primeira coleta real, registrando o resultado do SC-001 (meta fixa de 95%).
6. **P2, frontend:**
   1. **verificação (spike) do `fill-pattern` no globo**, com o Edge sem interface como na 001; se falhar, o plano B do `contracts/mapa-props-vistos.md`;
   2. estado (`modo`, `vistosMarcados`), `Preenchimento` e funções puras de cor; `padroes.ts`;
   3. adaptador (camada `padrao-rg`, imagem), `SeletorDeModo`, `useVistos` sob demanda, com os estados carregando, erro (mensagem na legenda e "Tentar de novo", territórios sem preenchimento, **nunca cinza**) e pronto;
   4. legenda de vistos (subitem, estado misto), `filtroDeVistos`, linha de fonte fora da parte recolhível, aviso de dados antigos;
   5. paleta e contraste (teste permanente); medição em 360 px e 1280 px;
   6. **painel recolhível** (FR-030), depois do estado (item 2) e do modo na tela: reducer, `BarraDoPainel`, `Painel`, ligação no `App` e o CSS de posição (seção "Painel recolhível", abaixo).
7. **Polimento:** `quickstart.md` conferido de ponta a ponta; atualizar `tasks.md`/checklists; relatório da primeira coleta (cobertura e tempo).

## Complexity Tracking

> Nenhuma violação da constituição. Esta tabela registra as **interpretações** e os desvios do pedido, todos aprovados em 28/10/2026.

| Item | Por que ocorre | Alternativa mais simples rejeitada porque |
|---|---|---|
| **Mover o cliente HTTP para a `infra`** (O11) | `vistos` não pode importar `coleta`, e o pedido manda mover o que for compartilhado para a `infra`. | Duplicar o cliente: duas cópias de uma regra de coleta responsável. |
| **Contrato completo da 002 substitui o da 001 nos testes** (O9) | O teste de contrato exige igualdade total; a 002 acrescenta uma rota e um campo. A parte da 001 fica **intacta**, e um teste dedicado falha se ela mudar. | Editar o arquivo da 001: reescreve o histórico de outra feature. |
| **Horário 05:13 e não 05:43** (O5) | O job mensal de postos roda no dia 1 às 05:43 e demora ~45 min; o worker tem um fio só. | Manter 05:43: funciona (tolerância de atraso), mas faz a coleta de vistos esperar quando o dia 1 cai numa segunda. |
| **Limite de 3 falhas técnicas seguidas** (O6) | O pedido diz "nova tentativa no dia seguinte" sem limite; sem limite, um formato quebrado geraria 2 requisições por dia para sempre. | Sem limite: contra o espírito do princípio IV. |
| **Estado `superada` na retenção** (O7) | A fonte pode mudar de novo antes de o dono decidir; sem fechar o registro antigo, haveria dois pendentes para o mesmo país. | Reaproveitar `revertida`: mistura "voltou ao valor exibido" com "mudou para outro valor". |
| **Dicionários dentro do pacote** (D5) | A imagem do Docker só copia `src`; as regras são do código e se testam com ele. | `dados/vistos/`: exigiria montar `dados/` também no worker e na imagem. |
| **Regra geral de categoria** (O1) | Rótulos como "Online visa required" e "e-VOA" misturam canal e exigência. | Decidir rótulo a rótulo sem regra: o próximo rótulo novo reabriria a discussão. |
| **`hash_observacao` nas regras por país** (O4) | A lista curada de "varia conforme o motivo" pode ficar velha quando a nota da fonte mudar; o hash faz o país voltar para revisão. | Heurística de texto: erraria em silêncio. |
| **Erro de `/vistos` sem cinza** (O10) | Cinza significa "sem informação de visto"; pintar tudo de cinza por falha de rede afirmaria uma coisa falsa. | Pintar de cinza e avisar: o mapa mentiria enquanto o erro durasse. |
