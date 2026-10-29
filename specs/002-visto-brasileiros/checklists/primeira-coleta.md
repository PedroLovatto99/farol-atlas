# Primeira coleta real de vistos (T094 a T097)

Registro de 29/10/2026. Banco de desenvolvimento do Docker Compose do projeto. Nenhum conteúdo do `.env` nem chave do LLM foi exibido ou registrado aqui.

## Origem da coleta id 1

A coleta registrada abaixo (id 1) **não foi disparada com `coletar --vistos`**. Começou às 13:02:44 UTC e terminou às 13:04:35 UTC, antes de a migração ser aplicada e os contêineres serem recriados nesta sessão (o `worker` novo subiu às 13:08:29).

**Origem provável** (informada pelo dono do projeto em 29/10/2026): o job `vistos-na-partida` do `worker`, que coleta ao subir quando nunca houve tentativa. Ele disparou quando o Docker Desktop religou os contêineres às 13:02 UTC, **ainda com o contato antigo no User-Agent** (o do `.env` antes do ajuste). Não pude conferir isso por conta própria: recriei o `worker` depois e os logs do contêiner anterior se perderam, e o registro da coleta não guarda o User-Agent.

Consequências:

- Não foi feita nenhuma coleta real a mais. Esta é a única coleta de vistos que existe, o que atende "uma única coleta real".
- **Esta coleta saiu com o contato antigo, não com o link do repositório** (`https://github.com/PedroLovatto99/farol-atlas`). Ela foi válida e sem bloqueio; as coletas seguintes já usam o contato do repositório, que foi conferido no `.env` e vale para os contêineres recriados.
- A conferência "antes de qualquer coleta" (quickstart seção 2) ficou impossível: o banco já tinha dados quando a validação começou.

## Resumo da coleta (T094)

| Campo | Valor |
|---|---|
| Resultado | `valida` (sem bloqueio, verificação humana, 403 ou 429) |
| Duração | 1 min 51 s (13:02:44 a 13:04:35 UTC), incluindo a tradução |
| Linhas lidas | 249 |
| Países reconhecidos | 228 (mínimo na primeira coleta: 150) |
| Última edição do artigo | 19/10/2026 05:08 UTC (revisão 1380975986) |
| Aplicadas / retidas | 228 / 0 (primeira coleta não retém) |
| Adiamentos / falhas seguidas | 0 / 0 |

Contagem por categoria de `requisito_visto` (228 linhas da fonte):

| Categoria | Países |
|---|---|
| isento | 132 |
| autorizacao_eletronica | 58 |
| visto_exigido | 24 |
| visto_na_chegada | 11 |
| outra_situacao | 3 |

Dos 228: 8 aceitam só o RG, 2 variam conforme o motivo. Permanência: 148 padronizada, 75 sem permanência, 3 em texto original (inglês), 2 "varia conforme o motivo".

## Cobertura (SC-001, meta fixa de 95%)

`GET /api/v1/vistos` devolve 238 territórios: o Brasil (`nao_se_aplica`) e **237 com painel**. Nos 237, a situação é: isento 133, autorização eletrônica 61, visto exigido 29, visto na chegada 11, outra situação 3, **sem informação 0**.

**Cobertura: 237 de 237 (100%) com rótulo conhecido. SC-001 atendido (≥ 95%).** Os 9 territórios além das 228 linhas da fonte usam a entrada do soberano.

As 3 "outra situação" têm rótulo conhecido (`rotulo_conhecido`), nenhuma por rótulo desconhecido: AS (Entry permit required), CLP (Special permit required) e SH (Visa not required / eVisa / Permission required).

## Pendências

Saída de `vistos pendentes`, conferida depois da coleta:

| Tipo | Quantidade |
|---|---|
| Mudanças retidas | 0 |
| Nomes não reconhecidos | 0 |
| Rótulos não reconhecidos | 0 |
| Regras por país a reconfirmar | 0 |

SC-009 e SC-010 atendidos: nenhum nome nem rótulo pendente. As tabelas `item_para_revisao` e `mudanca_retida` estão vazias.

## Traduções

110 observações em 109 países, **todas traduzidas** (110 com tradução, 0 sem). O tradutor é o padrão (`LLM_TRADUTOR` vazio, então vale o modelo do classificador). Não conferi a qualidade das traduções uma a uma, só amostras (Argentina, abaixo).

## Roteiro do quickstart, seção 4, passos 1 a 8 (T095)

Conferido pela API (`GET /api/v1/paises/{código}`). **O painel foi conferido no navegador pelo dono do projeto em 29/10/2026, que aprovou a P1.** A renderização da seção também está coberta pelos testes do frontend (commit 6dd6139).

| # | Passo | Resultado | Conferido |
|---|---|---|---|
| 1 | Argentina | isento, `aceita_rg = true`, rótulo "Freedom of Movement", 1 observação traduzida ("A entrada é permitida com uma carteira de identidade válida…"), dado de 29/10/2026 | Sim (API) |
| 2 | Estados Unidos | `visto_exigido`, sem permanência | Sim (API) |
| 3 | Tailândia, Omã, Austrália | Tailândia: isento, "3 meses". Omã: `autorizacao_eletronica` com rótulo combinado "Visa not required / eVisa", permanência original "14 days / 30 days". Austrália ("Online visa required"): `visto_exigido` | Sim (API). A categoria esperada da Tailândia no `research.md` 3.1 não foi comparada: o arquivo não cita a Tailândia |
| 4 | Jamaica | isento, `varia_conforme_motivo = true`, permanência `varia_conforme_motivo` | Sim (API) |
| 5 | Hong Kong, Guernsey, Kosovo, Malvinas | Hong Kong: entrada própria (isento). Guernsey: `origem = soberano`, "Reino Unido", autorização eletrônica, "6 meses". Kosovo: painel da Sérvia, `territorio_nome = "Kosovo"`, linha própria (isento). Malvinas: painel da Argentina, `territorio_nome = "Ilhas Malvinas"`, `aceita_rg = false` | Sim (API) |
| 6 | Brasil | `visto = null` | Sim (API) |
| 7 | Etiópia | `autorizacao_eletronica` ("eVisa / Visa on arrival"), permanência `original` = "up to 90 days" (a tela mostra "não traduzido") | Sim (API); o "não traduzido" na tela só por teste |
| 8 | Coleta sem tradutor | — | **Coberto pelos testes automatizados; execução manual dispensada** para não gerar uma coleta real extra (decisão do dono, 29/10/2026). Backend, `tests/integracao/vistos/test_servico_coleta.py`: `test_sem_tradutor_a_coleta_segue_e_as_observacoes_ficam_em_ingles`, `test_tradutor_que_falha_deixa_a_traducao_nula_e_a_coleta_continua_valida` e `test_a_coleta_seguinte_tenta_de_novo_a_traducao_que_falhou`. Frontend, `SecaoVisto.test.tsx`: "sem tradução, mostra o original em inglês avisando que não foi traduzido" |

Também lidos: Taiwan (`visto_exigido`, "Taiwan (China)", entrada própria), Porto Rico (`visto_exigido`, entrada própria) e Santa Helena (`outra_situacao`, rótulo à vista).

## Retenção por país (T096)

**Coberta pelos testes automatizados; execução manual dispensada** pelo dono em 29/10/2026, porque o roteiro da seção 5 exigiria pelo menos duas coletas reais novas (uma para reter e confirmar, outra para rejeitar). Os testes, em `backend/tests/integracao/vistos/`:

- `test_servico_coleta_retencao.py`: mudança para menos exigente retida mesmo com um único país (12a e 12b), `test_passar_a_aceitar_so_o_rg_fica_retido` (12h), retenção que some quando a fonte volta, `test_rejeitada_nao_reabre_com_o_mesmo_valor_da_fonte` e `test_rejeitada_e_superada_quando_a_fonte_muda_para_outro_valor_e_a_decisao_recomeca`;
- `test_servico_dono.py`: `vistos pendentes` (a lista com a categoria exibida, a lida e a data do dado exibido), `test_confirmar_aplica_o_candidato_com_a_data_da_coleta_que_o_leu`, `test_depois_de_confirmar_a_coleta_seguinte_nao_retem_de_novo`, `test_rejeitar_mantem_o_dado_antigo_e_marca_a_mudanca_como_rejeitada` e `test_rejeitar_vale_enquanto_a_fonte_mantem_o_valor_e_recomeca_se_ela_mudar`;
- o painel que continua com o dado antigo enquanto há retenção está em `test_leitura.py`.

## Checagens completas (T097)

Rodadas depois da coleta, com o `postgres-teste` de pé:

- `uv run poe verificar` (backend, com integração): passou. ruff, formato e mypy sem problemas, import-linter com 8 contratos mantidos, **1502 testes passaram**, `pip-audit` sem vulnerabilidades.
- `npm run verificar` (frontend): passou. eslint, prettier e `tsc` sem problemas, **477 testes passaram** em 38 arquivos, `npm audit` sem vulnerabilidades.

Ponto de controle da fase 2 (T097): checagens verdes, 8 contratos mantidos e a P1 aprovada pelo dono depois de conferir o painel no navegador (29/10/2026).

---

# Validação da P2 e ponto de controle da fase 3 (T126 a T128)

Registro de 29/10/2026. Usou os dados que já estavam no banco: **nenhuma coleta real** (Wikipédia, gov.br ou LLM) foi feita. Navegador: Edge sem interface (`--headless=new`), dirigido por um script do DevTools Protocol fora do repositório; globo com renderização por software. Capturas em [`capturas/`](capturas/). Toque simulado no celular (360×740, `mobile`), mouse e teclado no computador (1280×800).

## T126: passos 9 a 14 e 17 do quickstart

| # | Resultado | Onde |
|---|---|---|
| 9 | **OK** (1280 e 360). Cores de visto, legenda de visto (7 linhas, com o Brasil explicado), sem as bordas regionais (o Congo, com borda marrom em "Alertas", perde a borda), contorno escuro, linha "Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em 29/10/2026" | `1280-vistos-legenda.png` |
| 10 | **OK**. Depois de escolher "Vistos" e recarregar, volta a "Alertas" | (texto) |
| 11 | **OK** em 360 px, "Vistos", legenda recolhida (padrão no celular). A linha de fonte (x 8–352, y 605–648) não sobrepõe o botão da legenda, o aviso, o seletor, o "Sobre" nem os controles de zoom. Sem rolagem horizontal (`scrollWidth` 360) | `360-vistos-legenda-recolhida.png` |
| 12 | **OK**. Ao desmarcar "Isento, entrada com RG": "Isento de visto" mostra `aria-checked="mixed"` e o texto "(parcial)", a Argentina e os vizinhos de RG visíveis na captura ficam esmaecidos (listras), e a Alemanha (isento sem RG) continua cheia. Remarcar volta ao estado normal. O estado "parcial" também aparece em 360 px | `1280-vistos-rg-desmarcado.png`, `1280-vistos-rg-desmarcado-europa.png`, `360-vistos-legenda-aberta.png` |
| 13 | **OK**. O texto do painel da Argentina é **idêntico** nos dois modos, em 1280 e em 360 px | `1280-argentina-alertas.png`, `1280-argentina-vistos.png`, `360-argentina-vistos-painel.png` |
| 14 | **OK**. Brasil em "Vistos" tem o neutro claro, distinto do cinza de "sem informação"; a legenda o explica ("Brasil: seu país, sem seção de visto"); o painel dele não tem seção de visto | `1280-brasil-vistos.png` |

### Passo 17, painel recolhível (FR-030)

| Verificação | 1280 px | 360 px |
|---|---|---|
| Recolher por clique (computador) e por toque (celular) | OK: vira a barra, o país continua selecionado | OK |
| Expandir tocando na barra | OK | OK |
| Teclado: Tab até "Recolher painel" (13 Tabs a partir da busca), Enter e Espaço, nos dois sentidos | OK; o foco acompanha o botão que passa a valer ("Expandir painel: …" na barra; "Recolher painel" no painel) | OK (Enter e Espaço; o Tab não foi repetido) |
| Situação na barra | "Isento de visto" em "Vistos"; "Sem alerta do Itamaraty" em "Alertas" | idem |
| A barra não cobre legenda, linha de fonte, aviso, seletor nem "Sobre" | OK. Barra em x 932–1272, y 64–123: abaixo do "Sobre" (termina em y 54) | OK. Barra em y 673–732; linha de fonte em y 549–592; legenda recolhida em y 600–644 |
| Com a legenda **aberta** | — | A legenda termina em y 644, acima da barra (673): sem sobreposição |
| Controles de zoom | Ficam livres no canto inferior direito | Sobem para y 584–642, **acima da barra** |
| "Ver mundo" na barra | OK: fecha o painel, o globo volta ao mundo, o foco vai ao campo de busca | OK |
| Selecionar outro país | Abre expandido | Abre expandido |
| Recarregar | Abre sem painel | — |
| Rolagem horizontal | — | Nenhuma |

**Nome de país mais longo (360 px):** "Ilha Christmas e Ilhas Cocos (Austrália)" (41 caracteres, `IOA`; empata em 41 com "Ilhas Virgens Americanas (Estados Unidos)"). Com o painel aberto o nome quebra em duas linhas no cabeçalho, sem cortar; **recolhido, o nome aparece em uma linha cortada com reticências** ("Ilha Christmas e Ilhas Cocos…") e a situação ("Visto exigido") aparece inteira. Ver o desvio 1 abaixo. Capturas: `360-longo-painel-aberto-vistos.png`, `360-longo-barra-vistos.png`, `360-longo-barra-legenda-aberta.png`, `360-longo-barra-alertas.png`.

**Enquadramento do país recolhido (decisão de câmera do `plan.md`):**

- **1280 px:** bom. A Argentina continua inteira e à esquerda do centro (`1280-barra-vistos.png`).
- **360 px (corrigido em 29/10/2026, ver abaixo):** **mal enquadrado**. O país fica na metade de cima, porque o enquadramento ao selecionar reserva a área do painel aberto (gaveta de 55% da altura). Com a barra, sobra uma área grande vazia embaixo, e a parte norte da Argentina fica atrás do campo de busca e do seletor de modo (`360-argentina-barra-vistos.png`). Com o painel aberto, a parte norte também fica atrás desses controles (`360-argentina-painel-aberto-vistos.png`), o que já era assim antes da barra. **Registrado para a decisão:** se o ajuste de câmera do `plan.md` (pedido `garantir-visivel` ao recolher) vale a pena. Nenhuma mudança foi feita.

### SC-004

Do site aberto (navegação) até a seção de visto da Argentina visível, **incluindo a busca**, 3 execuções por tamanho:

| Largura | Tempos totais |
|---|---|
| 1280 px | 2073 ms, 1197 ms, 822 ms |
| 360 px | 1147 ms, 1113 ms, 741 ms |

**Pior caso: 2,1 s, bem dentro dos 10 s. SC-004 atendido.** Ressalva: o script cola o texto na busca em vez de digitar, então o tempo de digitação de uma pessoa não está incluso; a API e o frontend rodam na própria máquina, sem latência de rede real.

### Spike da T098

A verificação original (T098) está em `contracts/mapa-props-vistos.md`: `fill-pattern` no globo e clique em território com `fill-opacity: 0` passaram, sem Plano B. Nesta rodada, no app real, o padrão de listras aparece nos países de RG nos dois tamanhos, e a busca por um país abre o painel nos dois modos.

## T127: passos 15 e 16 (erro de `/vistos`)

- **Passo 15: OK.** Com o site aberto em "Alertas", `docker compose stop api` e escolher "Vistos": a legenda mostra "Não foi possível carregar os vistos." com o botão "Tentar de novo" e a linha "Vistos: dados indisponíveis no momento". **Nenhum país em cinza**: todos ficam sem preenchimento (só o oceano e os contornos). Captura `1280-vistos-erro-api-parada.png`.
- **Passo 16: OK.** `docker compose start api`, esperei a API responder 200 (3,2 s) e toquei em "Tentar de novo": os vistos carregam e o globo é pintado, com a legenda normal. Captura `1280-vistos-recuperado.png`.

## T128: ponto de controle da fase 3

| Checagem | Resultado |
|---|---|
| `cd backend; uv run poe verificar` (com o `postgres-teste`) | **Passou.** ruff e formato sem problemas, mypy sem erros em 143 arquivos, import-linter **8 contratos mantidos**, **1502 testes passaram** (6 min 8 s), `pip-audit` sem vulnerabilidades |
| `cd frontend; npm run verificar` | **Passou.** eslint, prettier e `tsc` sem problemas, **717 testes em 48 arquivos**, `npm audit` sem vulnerabilidades |
| `npm run build` | **Passou** (com o aviso de bloco maior que 500 kB) |
| Testes do painel recolhível (T129 a T136) | Verdes, dentro dos 717 |
| `niveis.ts` e `niveis.test.ts` | **Sem alteração** desde antes da fase 3 e desde antes da 002 |
| `specs/001-mapa-alertas-viagem/` | **Nada mudou** (diff vazio desde antes da 002) |
| Dependência nova | **Nenhuma.** `package.json` e `package-lock.json` não mudaram; em `backend/pyproject.toml` só mudaram os contratos do import-linter |

## Desvios e observações

1. **Nome longo na barra recolhida (resolvido em 29/10/2026):** o dono manteve o comportamento do código (uma linha com reticências; nome completo no nome acessível e no `title`) e `spec.md` e `plan.md` foram atualizados. Texto original do desvio: o `spec.md` (cenário 20) e o `plan.md` pedem que o nome quebre em até duas linhas; o código usa `truncate` (uma linha, reticências, `title` com o nome inteiro e nome acessível completo), e `BarraDoPainel.test.tsx` (T131) trava isso (`not.toMatch(/line-clamp|break-words/)`). A situação nunca é cortada. É uma divergência entre o texto da especificação e o que foi implementado e testado; **decisão do dono**: ajustar o código ou a especificação.
2. **Testes da 001 mexidos na fase 3 (aceito pelo dono em 29/10/2026, com nota na T128):** os asserts não mudaram, mas `cor.test.ts`, `feicoes.test.ts` e `testes/mapa-falso.test.tsx` tiveram imports e fixtures adaptados à nova forma de `MapaProps` (`preenchimento` no lugar de `nivel`). `niveis.test.ts` e o backend não foram tocados nesta fase. É menos que o "sem alteração" literal da T128.
3. **Atribuição "Fronteiras: Natural Earth" no celular (resolvido em 29/10/2026):** o crédito agora sobe para acima da barra recolhida (y 646–670, entre a legenda e a barra, que começa em 673); com o painel aberto ele fica atrás da gaveta, e o "Sobre" já traz o Natural Earth, com link, em "Fontes". Texto original do desvio: com a barra recolhida (e com o painel aberto, como antes) ela fica **atrás** do painel (y 706–730 contra a barra em 673–732). Não está na lista do FR-030 (legenda, linha de fonte, aviso, "Sobre"), mas vale saber; o link "Sobre as fronteiras deste mapa" continua na legenda.
4. **Passo 15, ordem:** com a API parada **antes** de abrir o site, o `/mapa` também falharia e o globo nem seria pintado. Fiz como a T127 descreve: site aberto com a API de pé, em "Alertas", derrubei a API e escolhi "Vistos".
5. **`docker compose start api`** executa de novo o serviço `migracao` (dependência do Compose): `alembic upgrade head` e seed, sem coleta e sem dado novo.
6. **Passo 8 e seção 5 do quickstart:** não repetidos, continuam cobertos pelos testes (dispensa de 29/10/2026).
7. **Primeira tentativa do passo 16** falhou por pressa do script (toquei antes de a API voltar): erro da minha automação, não do site. A segunda rodada esperou a API responder e passou.
8. **Limite da medição:** a renderização do globo é por software no Edge sem interface; as capturas mostram as cores e as listras reais, mas não o desempenho de um celular de verdade. Não testei num aparelho físico.

## Ajustes depois da validação (29/10/2026, decisões do dono)

- **Câmera no celular:** a cada recolher ou expandir, o país selecionado vai ao centro da área visível (de baixo do cabeçalho até a barra ou a gaveta), sem mudar o zoom; com movimento reduzido, sem animação. No computador nada mudou. Conferido no navegador em 360 px com a Argentina: recolhido, o país fica centralizado entre o seletor de modo (cabeçalho termina em y 214) e a barra (y 673); expandido, na área acima da gaveta (`360-novo-2-barra.png`, `360-novo-3-expandido.png`).
- **Crédito das fronteiras:** com a barra, ele fica em y 646–670, acima da barra (673) e abaixo do botão da legenda (termina em 644).
- **Nome longo:** fica como está; `spec.md` e `plan.md` atualizados.
- **Situação da barra em uma linha:** sem o rótulo curto, "Autorização ou visto eletrônico" quebrava em 320 px (barra de 59 para 79 px). Agora a barra usa o rótulo curto; em 320 e 360 px todos os casos medidos ficam com 59 px, inclusive o pior caso "Ilhas Malvinas: Eletrônico" (`320-barra-kosovo.png`). Title e nome acessível levam o rótulo completo.
