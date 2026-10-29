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
