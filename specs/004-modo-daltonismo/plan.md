# Implementation Plan: Modo de cores para daltonismo

**Branch**: `004-modo-daltonismo` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-modo-daltonismo/spec.md`

## Summary

Um botão "Modo daltonismo" troca as cores do globo, da legenda e do painel por paletas próprias, só
no frontend. O backend, a API e os dados não mudam. A preferência é um `useState` na `Tela`, lido de
forma síncrona do `localStorage` (como a preferência da legenda), então a primeira pintura já sai
certa e alternar não toca no reducer: seleção, filtros, painel, câmera e modo do globo continuam
como estavam, sem nenhum pedido novo à API.

- **Alertas**: paleta nova, com pior distância de **13,4** (mínimo exigido: 12). "Não viaje" ganha
  hachura cruzada e "evite" ganha pontos. A borda de "evite" fica tracejada. O contorno dos países
  passa a ser o escuro do modo "Vistos" (`#1F2A44`, 0,6 px), com contraste de pelo menos 4,16:1 contra
  as quatro cores e 11,45:1 contra o oceano, para "sem alerta" não se confundir com o mar (FR-008a).
- **Vistos**: a rampa da 002 já passa; só a cor das listras do RG muda, de `#1F2A44` para `#0E2A20`.
  A pior distância é **12,1**.

Detalhes: [research.md](research.md), [contracts/](contracts/) e [quickstart.md](quickstart.md). Sem
`data-model.md`: a única informação nova é um booleano no navegador, descrito em
[contracts/interface-do-modo.md](contracts/interface-do-modo.md).

## Technical Context

**Language/Version**: TypeScript `strict: true`. Igual à 001, à 002 e à 003.

**Primary Dependencies**: as atuais (React 19, Vite, Tailwind, MapLibre GL JS 6.15). **Nenhuma
dependência nova.**

**Storage**: `localStorage`, chave `farol-atlas:daltonismo`. Sem migração, sem mudança no banco.

**Testing**: Vitest + Testing Library, com `MapaFalso` e `criarApiSimulada`. As distâncias são
testadas com `distanciaEntreCores` e `simularDaltonismo`.

**Target Platform**: navegadores atuais, a partir de 360 px.

**Project Type**: web-application (só o frontend muda).

**Performance Goals**: mudança visível em menos de 1 s (SC-005). Alternar custa um `setData`, o
mesmo que trocar entre "Alertas" e "Vistos".

**Constraints**: com o modo desligado, a aparência é exatamente a atual (FR-015). Nenhum texto muda
além do botão (FR-014).

**Scale/Scope**: 1 botão, 1 preferência, 2 paletas, 2 padrões novos e 1 estilo de linha.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (constituição v1.0.3)

| Princípio | Resultado | Como o plano atende |
|---|---|---|
| I. Qualidade por ferramenta | Passa | Código sob `npm run verificar` (ESLint, Prettier, `tsc` strict, Vitest, auditoria); sem `any`. |
| II. TDD | Passa | Paletas, padrões, preferência, botão e fluxo na `Tela` começam por teste que falha. Na interface, comportamento: nome, estado, dados entregues ao mapa. |
| III. Arquitetura | Passa | Regras em funções puras (`cor.ts`, `padroes.ts`, `feicoes.ts`); o adaptador só registra imagens e camadas, e continua sendo o único a importar `maplibre-gl`. O botão recebe tudo por props. Carregamento do mapa intacto. |
| IV. Coleta responsável | Não se aplica | Nada de coleta. |
| V. Informação confiável | Passa | Nenhum dado, nível ou texto muda. "Não verificado" continua cinza e sem padrão, e território sem dado continua "não verificado". |
| VI. Acessível e celular | Passa | É o objetivo da feature: padrões e tracejado tiram a dependência da cor. Botão com `aria-pressed`, teclado, foco visível e alvo de 44 px; funciona em 360 px; nenhuma animação nova. |
| VII. Simples e gratuito | Passa | Nada novo na infra. |
| VIII. Segurança | Passa | A preferência fica no navegador; nada vai ao servidor. O valor guardado é comparado com um literal, e qualquer outro vale "desligado". |
| Idioma | Passa | Tudo em português. |

**Re-checagem após o desenho:** sem violações; Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/004-modo-daltonismo/
├── plan.md
├── research.md                   # D1 a D9
├── quickstart.md
├── contracts/
│   ├── paletas-e-padroes.md      # cores exatas, distâncias, contrastes, padrões e bordas
│   └── interface-do-modo.md      # botão, preferência, props e propriedades do mapa
├── checklists/requirements.md
└── tasks.md                      # /speckit-tasks
```

### Source Code (repository root)

```text
frontend/src/
├── App.tsx                                # estado do modo; repassa `daltonismo`
├── compartilhado/tema.css                 # tokens --color-daltonismo-*
├── funcionalidades/
│   ├── daltonismo/                        # NOVO
│   │   ├── BotaoDoDaltonismo.tsx (+ teste)
│   │   └── preferencia.ts (+ teste)       # mesmo padrão de legenda/preferencia.ts
│   ├── mapa/
│   │   ├── cor.ts                         # paletas e `paletaDe`; preenchimentos com `daltonismo`
│   │   ├── contorno.ts                    # `contornoDosPaises(modo, daltonismo)`
│   │   ├── padroes.ts                     # matriz genérica, hachura, pontos, amostras
│   │   ├── feicoes.ts                     # `imagem_do_padrao`, `borda_tracejada`
│   │   ├── tipos.ts                       # `Preenchimento.padrao`, `MapaProps.daltonismo`
│   │   └── adaptador-maplibre.tsx         # imagens, camadas de padrões e tracejada, contorno
│   ├── legenda/Legenda.tsx                # amostras com padrão e amostra da borda
│   ├── legenda/LegendaRecolhivel.tsx      # repassa `daltonismo`
│   ├── vistos/LegendaDeVistos.tsx         # listras e cores pela paleta
│   └── painel/Painel.tsx                  # selo e bordas das regiões pela paleta
└── testes/mapa-falso.tsx                  # expõe `daltonismo`
```

**Structure Decision**: uma funcionalidade nova, `funcionalidades/daltonismo`, para o botão e a
preferência. As paletas ficam em `mapa/cor.ts`, onde já estão as cores do mapa e de onde a legenda e
o painel já importam. Backend, `esquema.d.ts` e OpenAPI não mudam.

## O que reaproveita

| Existente | Uso nesta feature |
|---|---|
| `tema.css` + teste que compara hex e token | Tokens `--color-daltonismo-*`, conferidos da mesma forma |
| `distanciaEntreCores`, `simularDaltonismo` (`distanciaDeCor.ts`), `contraste` | Mesmos cálculos da 002; a tabela do contrato foi gerada com eles e vira teste |
| `CORES_DE_VISTO`, `NIVEIS`, `COR_DA_BORDA_REGIONAL` | A paleta padrão aponta para eles, então o modo desligado não ganha cor nova (FR-015) |
| `matrizDasListras`, `styleimagemissing`, `fill-pattern` | Generalizados para os padrões novos |
| `lerPreferenciaDaLegenda`, `gravarPreferenciaDaLegenda` | Mesmo try/catch, em `daltonismo/preferencia.ts` |
| `CONTORNO_DO_MODO_VISTOS` (`contorno.ts`) | O mesmo contorno, usado também em "Alertas" com o modo ligado |
| `SeletorDeModo` | Mesmo visual de ativo (fundo escuro e negrito) e mesmo foco |

## Riscos

- **Largura em 360 px**: a estimativa é 335 px de 344 disponíveis no grupo do cabeçalho. Só o
  navegador confirma; `flex-wrap` evita que o conteúdo estoure se faltar espaço.
- **Borda sobre "não verificado"**: o contraste cai para 2,94 (vermelha) e 1,57 (marrom). A distância
  segue acima de 12, e o tracejado e o painel ajudam. Só ocorre em país "não verificado" com região
  em alerta. Ver [contrato](contracts/paletas-e-padroes.md#contraste).
- **Padrões em tela de alta densidade**: seguem a escala das listras do RG. Confirmar no aparelho
  (quickstart, passo 4).

## Complexity Tracking

Sem violações.
