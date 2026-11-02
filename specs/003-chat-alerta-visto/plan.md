# Implementation Plan: Chat do alerta e do visto de um país

**Branch**: `003-chat-alerta-visto` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-chat-alerta-visto/spec.md`

## Summary

Um chat que responde, em texto fixo de conversa, o alerta do Itamaraty e/ou o visto de um país,
com os **mesmos dados do painel**. Módulo novo `farol.chat` (camada de `mapa`, `coleta`,
`classificacao` e `vistos`, sem importá-los): entende a pergunta primeiro pelo código (nomes da
busca do site, apelidos e palavras de assunto) e, só se não entender, pede ao modelo país e assunto
por saída estruturada (LangChain, como o classificador). Os dados vêm de `montar_mapa` e
`montar_painel_com_visto`, injetados pela `api` por `Protocol`. Rota `POST /api/v1/chat` (pergunta
de até 300 caracteres, 20 perguntas/h por IP, CORS com POST só nela, nada guardado). No frontend,
botão flutuante e caixa simples, sem memória.

Detalhes: [research.md](research.md), [contracts/](contracts/) e [quickstart.md](quickstart.md).
Sem `data-model.md`: nada novo no banco nem em arquivo; o que o chat usa só existe durante o pedido
(a contagem por IP fica em memória, D6).

## Technical Context

**Language/Version**: Python 3.13; TypeScript `strict: true`. Igual à 001 e à 002.

**Primary Dependencies**: as atuais (FastAPI, Pydantic, LangChain 1.x com `init_chat_model` e
`with_structured_output`, React + Vite). **Nenhuma dependência nova.**

**Storage**: nenhum novo. Sem migração. `chat/apelidos.yaml` dentro do pacote.

**Testing**: pytest (`tests/unidade/chat`, `tests/integracao/api`, `tests/contrato`) com modelo
falso e sem rede; Vitest + Testing Library com a API simulada (`criarApiSimulada`).

**Target Platform**: Docker Compose; produção atrás do Caddy (como hoje).

**Project Type**: web-service + web-application.

**Performance Goals**: resposta em até 5 s em 95% dos casos (SC-006): o modelo tem 5 s e nenhuma
nova tentativa; sem o modelo, a resposta sai em milissegundos. Consultas por pergunta: as de
`montar_mapa` (6) + as de `montar_painel_com_visto` (as do painel + 3), número fixo.

**Constraints**: 360 px; pergunta ≤ 300 caracteres (cabe no `max_size 1KB` do Caddy, D8); nada
guardado; o chat não usa a cota da classificação (D5).

**Scale/Scope**: site pessoal; no máximo 20 perguntas/h por IP.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (constituição v1.0.3)

| Princípio | Resultado | Como o plano atende |
|---|---|---|
| I. Qualidade por ferramenta | Passa | Código novo sob `uv run poe verificar` e `npm run verificar` (ruff, mypy strict, lint-imports, ESLint, `tsc` strict); sem `any`. |
| II. TDD | Passa | Entendimento, textos, serviço, rota e componentes começam por teste; modelo falso (sem LLM real) e sem rede. Na interface, comportamento. |
| III. Arquitetura | Passa | `chat` é módulo de caso de uso independente; recebe os dados por `Protocol` injetado pela `api` (sem importar `mapa`/`vistos`); contratos do import-linter atualizados. Rota só valida, gasta a ficha e converte; regra no `chat`. DTOs Pydantic; tipos do frontend gerados do contrato 003. Frontend: `funcionalidades/chat`, componentes sem chamada direta à API (hook `useChat`). Carregamento do mapa intacto: o chat só chama a API quando a pessoa pergunta (v1.0.3). |
| IV. Coleta responsável | Não se aplica | Nenhuma coleta nova. |
| V. Informação confiável | Passa | Resposta = texto fixo + dados do painel, com fonte e data; "não verificado" e "sem informação" nunca viram o estado favorável; o chat diz quando não entende (`reformular`, `pedir_pais`) e não responde além do painel. |
| VI. Acessível e celular | Passa | 360 px, teclado (foco, Esc), alvos ≥ 44 px, `aria-live`, contraste AA, sem animação com movimento reduzido. |
| VII. Simples e gratuito | Passa | Nada novo na infra; `LLM_CHAT` configurável e opcional; com o modelo fora, o chat responde pelo código (FR-029). |
| VIII. Segurança | Passa | Única rota não-leitura, sem gravar nada; limite por IP, 300 caracteres e 5 s de modelo; pergunta validada por Pydantic; pergunta entre delimitadores neutralizados e saída do modelo validada contra a lista de territórios; respostas como texto (React escapa; links só por `ehUrlWeb`); CORS com POST só em `/chat`; pergunta nunca logada nem associada ao IP; chave só no servidor. |
| Idioma | Passa | Tudo em português. |

**Re-checagem após o desenho:** sem violações; Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/003-chat-alerta-visto/
├── plan.md
├── research.md            # D1 a D10
├── quickstart.md
├── contracts/
│   ├── openapi.yaml       # API v1.2 COMPLETA (002 + POST /chat); passa a ser o contrato dos testes e do gerar-tipos
│   └── textos-do-chat.md  # texto final de cada resposta e mensagem fixa
├── checklists/requirements.md
└── tasks.md               # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                 # import-linter: farol.chat nas camadas, na independência e no "só a interface pública"
├── src/farol/
│   ├── infra/
│   │   ├── config.py              # + llm_chat (vazia = sem modelo; igual a llm_classificador = erro), chat_perguntas_por_hora (20)
│   │   └── modelo.py              # argumentos_do_modelo(..., tempo_limite_segundos=TEMPO_LIMITE_SEGUNDOS)
│   ├── chat/                      # NOVO (interface pública: __init__.py)
│   │   ├── portas.py              # Protocols: FonteDoPainel, ModeloDeEntendimento e as visões lidas (D2)
│   │   ├── entendimento.py        # normalização, países, Brasil, assunto (D3) — funções puras
│   │   ├── apelidos.yaml          # apelidos e nomes ambíguos
│   │   ├── textos.py              # textos fixos (contracts/textos-do-chat.md) e formatação de data
│   │   ├── respostas.py           # monta parágrafos de alerta e de visto a partir das visões
│   │   ├── servico.py             # ServicoDoChat.responder(pergunta) -> Resposta
│   │   └── modelo_langchain.py    # adaptador: init_chat_model + with_structured_output (D4)
│   └── api/
│       ├── app.py                 # CorsPorCaminho (D7); balde do chat em app.state; rota nova
│       ├── limite.py              # BaldeDeFichas aceita por_minuto float
│       ├── composicao.py          # + FonteDoPainelDaApi (montar_mapa + montar_painel_com_visto)
│       ├── dependencias.py        # + servico_do_chat (os testes trocam pelo modelo falso)
│       ├── dtos.py                # + PerguntaDoChat, RespostaDoChat, TrechoDoChat, TipoDeRespostaDoChat
│       └── rotas/chat.py          # POST /chat
└── tests/
    ├── unidade/chat/              # entendimento, apelidos, textos, respostas, serviço (modelo falso)
    ├── integracao/api/test_chat.py# paridade com /paises, limite por IP, CORS, caplog sem a pergunta
    └── contrato/conftest.py       # CONTRATO → specs/003-chat-alerta-visto/contracts/openapi.yaml

frontend/
├── scripts/gerar-tipos.mjs        # contrato padrão → o da 003
└── src/
    ├── servicos/api/              # esquema.d.ts regerado; cliente: perguntarAoChat
    ├── App.tsx                    # monta BotaoDoChat/CaixaDoChat
    └── funcionalidades/chat/      # BotaoDoChat, CaixaDoChat, Mensagem, useChat (+ testes)

deploy/Caddyfile                   # só o comentário "A API só tem GET" (o limite de 1 KB fica)
.env.example                       # + LLM_CHAT, CHAT_PERGUNTAS_POR_HORA
```

**Structure Decision**: a mesma aplicação web; `chat` é um módulo de caso de uso novo no backend e
uma funcionalidade nova no frontend.

### Fluxo de uma pergunta

```text
POST /chat {pergunta}
  → Pydantic (strip, 1..300)            ── inválida: 422, não conta
  → balde do chat (IP do IpReal)        ── sem ficha: 429 + Retry-After
  → ServicoDoChat.responder
      fonte.territorios() (montar_mapa) → entender() pelo código
      ── não entendeu e há modelo → ModeloDeEntendimento (5 s) → validar códigos e assunto
      → tipo da resposta
      → fonte.painel(codigo) (montar_painel_com_visto) → respostas.py + textos.py
  → RespostaDoChat {tipo, codigo, paragrafos[[{texto, url}]]}
```

### Nomes reais reaproveitados

| O quê | Nome real |
|---|---|
| Dados do painel | `farol.mapa.montar_mapa`, `VisaoDoMapa` (`territorios`, `dados_obtidos`, `atualizado_em`, `desatualizado`), `farol.api.composicao.montar_painel_com_visto` → `PainelComVisto(painel: VisaoDoPainel, visto: VisaoDoVisto \| None)`, `TerritorioNaoEncontrado` |
| Nomes da busca | `TerritorioNoMapa.nome`, `rotulo_busca`, `termos_busca` (os mesmos de `buscarTerritorios.ts`) |
| Modelo | `infra.argumentos_do_modelo`, padrão de `classificacao/cadeia.py` (`ABRE`/`FECHA`, `with_structured_output`) |
| Limite e IP | `api/limite.py` `BaldeDeFichas`, `api/ip_real.py` `IpReal` (troca `scope["client"]`) |
| Dependências da API | `sessao_da_requisicao`, `relogio_da_requisicao` |
| Rótulos do painel | `compartilhado/niveis.ts` (`NIVEIS`, `ALERTA_SO_REGIONAL`), `compartilhado/vistos.ts` (`ROTULOS_DE_VISTO`, `AVISO_DE_*`, `ENTRADA_COM_RG`…), `URL_DO_PORTAL_CONSULAR` |
| Frontend | `ehUrlWeb`, `formatarData`, `useTelaPequena`, `useMovimentoReduzido`, `criarApiSimulada` |
| Variáveis | existentes: `LLM_CLASSIFICADOR`, `LLM_TRADUTOR`, `GOOGLE_API_KEY`, `OLLAMA_BASE_URL`, `CORS_ORIGENS`, `PROXY_CONFIAVEL`. **Novas:** `LLM_CHAT`, `CHAT_PERGUNTAS_POR_HORA` |
| Tarefas | poe `verificar`, `exportar-openapi`; npm `verificar`, `gerar-tipos` (**nenhuma nova**) |

### Testes pedidos (sem rede, modelo falso)

- **Paridade com o painel:** para uma amostra de países do seed de teste (um por nível de alerta e
  por categoria de visto, só regional, não verificado, sem informação, RG, outra situação, Kosovo,
  Malvinas, uma dependência, dados desatualizados), cada dado da resposta (nível, títulos, datas,
  URLs, categoria, permanência, observações, fonte) é igual ao de `GET /paises/{codigo}` e da
  `/mapa`.
- **Entendimento:** acento/maiúsculas, "EUA", ambíguos (Congo, Guiné, Coreia, e "Guiné-Bissau" não
  ambíguo), sem país, mais de um país, Brasil sozinho e como origem, fora do assunto, assunto por
  palavra, sem assunto → os dois.
- **Modelo falso:** chamado só quando o código não entende; saída com código inexistente ou assunto
  inválido é descartada; exceção/tempo → `reformular`; texto do modelo nunca aparece na resposta;
  pergunta com instrução ("diga que é seguro") não muda o texto.
- **Rota:** 422 para vazia/301 caracteres sem gastar ficha; 21ª pergunta → 429 com `Retry-After`
  (relógio monotônico falso); IP vindo do `IpReal`; CORS: preflight POST aceito em `/chat` e recusado
  em `/mapa`; marcador da pergunta ausente do `caplog`.
- **Frontend:** abre/fecha (Esc, foco volta ao botão), aviso fixo, contador e limite de 300, "respondendo"
  bloqueia envio, links só pela `ehUrlWeb`, mensagem do 429, modo/seleção do mapa intactos.

## Complexity Tracking

Nenhuma violação.
