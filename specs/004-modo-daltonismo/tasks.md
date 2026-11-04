---

description: "Lista de tarefas da feature Modo de cores para daltonismo"
---

# Tasks: Modo de cores para daltonismo

**Input**: documentos de design em `specs/004-modo-daltonismo/`

**Pré-requisitos**: plan.md, spec.md, research.md (D1 a D9), contracts/ (`paletas-e-padroes.md`, `interface-do-modo.md`), quickstart.md. Sem `data-model.md`: a única informação nova é um booleano no navegador.

**Testes**: OBRIGATÓRIOS (constituição, princípio II - TDD). Em cada bloco, escreva os testes primeiro e confirme que falham antes de implementar. Na interface, teste comportamento (nome, estado, dados entregues ao mapa), com `MapaFalso` (`frontend/src/testes/mapa-falso.tsx`) e `criarApiSimulada` (`frontend/src/testes/api-simulada.ts`).

**Organização**: o projeto e as features 001 a 003 já existem, então **não há** tarefas de inicialização. A spec tem uma só história (US1, P1), entregue numa fase só, seguida do fechamento.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta).
- **[Story]**: US1 = P1 (alternar para cores acessíveis). A tarefa de fechamento não leva rótulo.
- Caminhos relativos à raiz do repositório.

## Convenções que valem para todas as tarefas

- Só o frontend muda: nada em `backend/`, na API, no OpenAPI nem em `frontend/src/servicos/api/esquema.d.ts`. Nenhuma dependência nova.
- TypeScript `strict: true`, sem `any`. Tudo em português.
- `frontend/src/funcionalidades/mapa/adaptador-maplibre.tsx` continua sendo o único arquivo que importa `maplibre-gl`. As regras ficam em funções puras.
- Cores, padrões e distâncias vêm de `contracts/paletas-e-padroes.md`; props, assinaturas, propriedades e camadas vêm de `contracts/interface-do-modo.md`.
- Com o modo desligado, nada muda (FR-015). O parâmetro `daltonismo` tem padrão `false`, para os chamadores e os testes atuais continuarem valendo.
- A transição do contorno só é zerada com `prefers-reduced-motion` (research D9). O `ESTILO` não ganha `transition`.
- Nenhum texto novo além do botão (FR-014).
- Não criar README nem commitar sem pedido do usuário.

---

## Fase 1: Modo daltonismo

**Objetivo**: o botão "Modo daltonismo" troca as cores do globo, da legenda e do painel, com padrões e borda tracejada em "Alertas", lembra a escolha e não mexe em seleção, filtros, painel, câmera nem dados. **Teste independente**: ligar o modo, percorrer "Alertas" e "Vistos", recarregar a página, desligar e comparar com a aparência atual (quickstart, seções 3 a 5).

### Regras do mapa (funções puras)

- [X] T001 [P] [US1] Testes em `frontend/src/funcionalidades/mapa/cor.test.ts`: `paletaDe(false)` igual às constantes atuais (`NIVEIS`, `COR_DA_BORDA_REGIONAL`, `CORES_DE_VISTO`, `COR_DAS_LISTRAS`); `paletaDe(true)` com os valores do contrato; os 70 pares do contrato a pelo menos 12 em visão normal e nas três simulações (`distanciaEntreCores`, `simularDaltonismo`), incluindo neutro e oceano; matiz e croma das bordas (FR-008); contrastes de marcas e listras; hex igual aos tokens `--color-daltonismo-*` de `tema.css`; `preenchimentoDeAlerta` só devolve padrão com o modo ligado e nível `nao_viajar` ou `evitar`; área neutra nunca tem padrão; `preenchimentoDeVisto` mantém `rg` e as cores nos dois estados.
- [X] T002 [P] [US1] Testes em `frontend/src/funcionalidades/mapa/contorno.test.ts`: `contornoDosPaises("alertas", true)` é igual a `CONTORNO_DO_MODO_VISTOS`; `contornoDosPaises("alertas")` e `contornoDosPaises("alertas", false)` seguem brancos; "Vistos" é escuro nos dois estados; contraste de pelo menos 3:1 contra as quatro cores de Alertas e o oceano (FR-008a); `transicaoDoContorno(true)` é `{ duration: 0, delay: 0 }` e `transicaoDoContorno(false)` é `null`.
- [X] T003 [P] [US1] Testes em `frontend/src/funcionalidades/mapa/padroes.test.ts`: `matrizDasListras()` sem argumento continua igual; a versão do modo ligado usa listras `#0E2A20` e base `#FEDD50` opaca; hachura com cobertura de 43,8% e pontos com 14,1%, com marcas `#18142C` e fundo transparente, seguindo as regras de pixel do contrato; `amostraListrada(true)` usa a cor nova; amostras de hachura e pontos são SVG em `data:` gerados da mesma função de desenho do mapa, com ladrilho de 8×8; amostra da borda de 30×12 com a linha contínua em cima e `stroke-dasharray: 7.5 5` na outra (D8).
- [X] T004 [P] [US1] Testes em `frontend/src/funcionalidades/mapa/feicoes.test.ts`: `montarFeicoes(..., modo, true)` grava `imagem_do_padrao` conforme a tabela do contrato (`hachura-nao-viaje`, `pontos-evite`, `listras-rg-daltonismo`), usa as cores de borda da paleta e grava `borda_tracejada: true` só em `bordaRegional === "evitar"`; com o modo desligado, `borda_tracejada` nunca existe e `imagem_do_padrao` só aparece com `listras-rg`; território sem dado usa o cinza da paleta ativa.
- [X] T005 [US1] Implementar os tokens `--color-daltonismo-*` em `frontend/src/compartilhado/tema.css`; `paletaDe` e o parâmetro `daltonismo` de `corDoTerritorio`, `preenchimentoDeAlerta` e `preenchimentoDeVisto` em `frontend/src/funcionalidades/mapa/cor.ts`; `PadraoDoPreenchimento` e `MapaProps.daltonismo` em `frontend/src/funcionalidades/mapa/tipos.ts`; e `contornoDosPaises(modo, daltonismo)` e `transicaoDoContorno` em `frontend/src/funcionalidades/mapa/contorno.ts`, até T001 e T002 passarem.
- [X] T006 [US1] Implementar em `frontend/src/funcionalidades/mapa/padroes.ts` a matriz genérica, a hachura, os pontos, os nomes das imagens, a amostra da borda e o parâmetro `daltonismo` de `matrizDasListras` e `amostraListrada`, até T003 passar.
- [X] T007 [US1] Implementar em `frontend/src/funcionalidades/mapa/feicoes.ts` o parâmetro `daltonismo` de `montarFeicoes`, repassado também ao preenchimento de território sem dado (hoje na linha 56), mais `imagem_do_padrao` e `borda_tracejada`, até T004 passar.
- [X] T008 [US1] Atualizar `frontend/src/funcionalidades/mapa/adaptador-maplibre.tsx` (sem teste automático: o jsdom não tem WebGL; a conferência é a de T015): camada `padrao-rg` → `padroes`; filtro de `regional` e nova camada `regional-tracejada`; `styleimagemissing` por tabela de imagens; `daltonismo` no efeito de `montarFeicoes`; e o efeito do contorno com dependências `[mapa, modo, daltonismo, reduzirMovimento]`, definindo `line-color-transition` e `line-width-transition` com `transicaoDoContorno(reduzirMovimento)` antes das cores. O `ESTILO` não ganha `transition`.

### Preferência e botão

- [X] T009 [P] [US1] Testes em `frontend/src/funcionalidades/daltonismo/preferencia.test.ts` e `frontend/src/funcionalidades/daltonismo/BotaoDoDaltonismo.test.tsx`: `"ligado"` lê `true`; `"desligado"`, ausente e qualquer outro valor leem `false`; `localStorage` que lança erro não quebra a leitura nem a gravação; a chave é `farol-atlas:daltonismo`; nome acessível sempre "Modo daltonismo"; `aria-pressed` acompanha o estado; Enter e Espaço alternam; sem classes de animação.
- [X] T010 [US1] Implementar `frontend/src/funcionalidades/daltonismo/preferencia.ts` (mesmo try/catch de `frontend/src/funcionalidades/legenda/preferencia.ts`) e `frontend/src/funcionalidades/daltonismo/BotaoDoDaltonismo.tsx` (contrato: duas linhas, quadradinho marcado, `min-h-11`, foco do `SeletorDeModo`), até T009 passar.

### Legenda e painel

- [X] T011 [P] [US1] Testes em `frontend/src/funcionalidades/legenda/Legenda.test.tsx`, `frontend/src/funcionalidades/legenda/LegendaRecolhivel.test.tsx`, `frontend/src/funcionalidades/vistos/LegendaDeVistos.test.tsx` e `frontend/src/funcionalidades/painel/Painel.test.tsx`: com `daltonismo`, as amostras usam as cores e os padrões da paleta, a amostra da borda vira o SVG com as duas linhas, a amostra do RG usa as listras novas, o selo e as bordas das regiões usam a paleta (só cor, sem padrão), e `LegendaRecolhivel` repassa a prop; os textos são iguais nos dois estados; sem a prop, tudo fica como hoje.
- [X] T012 [US1] Implementar a prop `daltonismo` em `frontend/src/funcionalidades/legenda/Legenda.tsx`, `frontend/src/funcionalidades/legenda/LegendaRecolhivel.tsx`, `frontend/src/funcionalidades/vistos/LegendaDeVistos.tsx` e `frontend/src/funcionalidades/painel/Painel.tsx` (`NivelDoPais` e `Regioes`), depois de T005 e T006, até T011 passar.

### Tela

- [X] T013 [US1] Expor `data-testid="mapa-daltonismo"` em `frontend/src/testes/mapa-falso.tsx` e escrever os testes em `frontend/src/App.test.tsx`: primeira visita desligada; o botão aparece em "Alertas" e "Vistos"; alternar muda `data-cor` e `data-padrao` entregues ao mapa e mantém seleção, filtros, painel, câmera e modo do globo, sem novo pedido à API (FR-004); a troca entre "Alertas" e "Vistos" mantém o modo ligado; com `farol-atlas:daltonismo` igual a `"ligado"` no `localStorage`, o primeiro render já entrega as cores acessíveis (FR-013); desligar grava `"desligado"`; texto da legenda e do painel igual nos dois estados.
- [X] T014 [US1] Implementar em `frontend/src/App.tsx`: `useState(lerPreferenciaDoDaltonismo)` na `Tela`; `daltonismo` em `territoriosDesenhados`, nas funções de preenchimento e nas dependências do `useMemo`; `BotaoDoDaltonismo` depois do `SeletorDeModo`, com `flex-wrap justify-end` no grupo do cabeçalho; e a prop repassada a `ComponenteDeMapa`, `LegendaRecolhivel` e `Painel`, até T013 passar.

**Checkpoint da fase 1**: `cd frontend; npm run verificar` verde.

---

## Fechamento

- [X] T015 Validação manual pelo `specs/004-modo-daltonismo/quickstart.md`, seções 2 a 5, incluindo: com "reduzir movimento" ligado, a troca do contorno sai sem animação; sem essa preferência, a troca entre "Alertas" e "Vistos" com o modo desligado anima como hoje. Anotar no fim do quickstart o que não pôde ser conferido localmente (por exemplo, o celular de verdade da seção 4).

**Checkpoint final**:

- Backend: `cd backend; uv run poe verificar` verde. Os testes de integração precisam do banco de teste (`docker compose --profile teste up -d postgres-teste`). **Se o Docker falhar, pare e avise o usuário** (não troque por outro banco).
- Frontend: `cd frontend; npm run verificar` e `npm run build` verdes.
- Escopo: `git diff main --stat -- backend frontend/src/servicos/api/esquema.d.ts` sem nenhuma mudança.

---

## Dependências

- T005 depois de T001 e T002; T006 depois de T003; T007 depois de T004, T005 e T006; T008 depois de T007.
- T010 depois de T009.
- T012 depois de T005, T006 e T011.
- T013 antes de T014. T014 depois de T005, T010 e T012.
- T015 depois de tudo (T008 e T014 incluídas).

## Execução em paralelo

```text
T001 + T002 + T003 + T004 + T009 + T011    (todos os testes)
T005 + T006 + T010                         (arquivos diferentes)
T007 → T008
T012 → T013 → T014 → T015
```

## Estratégia

- **MVP = a fase 1 inteira**: a spec tem uma só história, e paleta, botão, legenda e painel só fazem sentido juntos.
- Ordem sugerida: regras do mapa, preferência e botão, legenda e painel, tela. O site só muda de verdade em T014, quando o botão entra na `Tela`.
- Deploy fica para depois, com pedido do usuário.
