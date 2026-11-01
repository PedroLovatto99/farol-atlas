# Contrato: indexação dos trechos, agenda e comandos do worker

**Spec**: FR-004, FR-007, FR-008 | **Pesquisa**: [../research.md](../research.md) D3 | **Dados**: [../data-model.md](../data-model.md)

## 1. Quem faz o quê

| Peça | Camada | Papel |
|---|---|---|
| `farol.mapa.alertas_que_definem_nivel(sessao)` | `mapa` (adição pequena à interface pública) | `dict[int, frozenset[str]]`: id do alerta → códigos de território para os quais ele rege o nível (usa `calcular_niveis`; sem mudança de comportamento) |
| `farol.chat.indexar_pendentes(sessao, embeddador, vigor, *, tudo=False) -> ResumoDaIndexacao` | `chat` | Compara o índice com os alertas elegíveis e corrige; **idempotente**; só vetoriza o que mudou |
| `farol.worker.jobs.indexar_real(configuracoes, *, tudo=False)` | `worker` | Abre a sessão, calcula `vigor` pelo `mapa`, monta o `Embeddador` real e chama o `chat` |
| `TrechoAlertaRepositorio` | `dominio` | Único que fala SQL com `trecho_alerta` |

O `chat` nunca importa o `mapa`: o `vigor` chega como argumento.

## 2. O que `indexar_pendentes` faz, em ordem

1. Lista os alertas **elegíveis** (confirmados por coleta completa, `removido_em` nulo, página lida, classificação vigente `ok`), com a classificação e os países.
2. Para cada um, compara `(confirmado_hash, modelo_embedding configurado, dimensoes configurada, classificacao_id)` com o que há em `trecho_alerta` **para esse modelo e essa dimensão** (linhas de outros modelos não contam como indexado).
   - igual → só atualiza `em_vigor_para` e `paises` se mudaram (sem vetorizar);
   - diferente ou ausente → fatia o texto em trechos (intervalos de `alerta.texto`), vetoriza em lote com `RETRIEVAL_DOCUMENT` e troca os trechos do alerta **na mesma transação**.
3. Apaga os trechos de alertas **não elegíveis** (removidos, sem confirmação, sem classificação válida). **Não apaga** vetores de outros modelos: quem faz isso é o `reindexar` (abaixo), para uma troca de modelo nunca deixar um alerta sem nenhum vetor no meio do caminho.
4. Devolve `ResumoDaIndexacao`: alertas novos, atualizados, inalterados, apagados, trechos gravados, falhas.

Falha ao vetorizar um alerta (cota, rede): registra, **não mexe nos trechos antigos desse alerta** (se ainda forem do hash vigente) e segue para o próximo; o ciclo seguinte tenta de novo. Com `tudo=True`, ignora a comparação e refaz todos os trechos (usado ao trocar de modelo ou depois de mudar o fatiamento).

Fatiamento: parágrafos de `html_corpo` (`p`, `li`, títulos) agrupados até ~1.000 caracteres (máximo ~1.600), com sobreposição de um parágrafo, cada trecho gravado como `[inicio, fim)` em `alerta.texto`; parágrafo que não se localiza no `texto` vira fatiamento por frases. Teste: para todo trecho, `0 <= inicio < fim <= len(texto)` e os trechos cobrem o texto sem deixar buraco além do que a sobreposição permite.

## 3. Agenda

- Um **segundo executor** do APScheduler (`ThreadPoolExecutor(1)`, nome `indexacao`) roda o job `indexacao-periodica` a cada `INDEXACAO_INTERVALO_MINUTOS` (padrão 5), com `coalesce=True`, `max_instances=1`. Ele **não disputa** o executor único das coletas (o de postos leva ~45 min), então a regra de 15 minutos não depende de a coleta de postos terminar.
- Também roda **na partida** do worker (uma vez, logo depois que sobe) para recuperar o que ficou pendente com o worker parado.
- Com `COLETAS_AUTOMATICAS=false` o worker segue ocioso (**sem** job, como hoje); a indexação é manual (comandos abaixo). O `agendador_ocioso()` e seu teste não mudam.
- Os horários de coleta (06:17, 05:43 do dia 1, 05:13 de segunda) e a regra de "uma requisição por vez" ao gov.br e à Wikipédia **não mudam**.

## 4. Comandos (`python -m farol.worker …`, dentro do contêiner do worker)

| Comando | O que faz | Saída | Código de saída |
|---|---|---|---|
| `indexar` | Uma passada de `indexar_pendentes` e sai | resumo (novos, atualizados, inalterados, apagados, trechos, falhas) | 0 sem falhas; 1 com falhas de vetorização; 2 uso errado ou configuração |
| `indexar --tudo` | Refaz todos os trechos | idem | idem |
| `indexar --status` | Só olha: alertas elegíveis × indexados, modelo e dimensão no índice × configurados, trechos sem vetor | tabela curta | 0 se tudo em dia; 1 se há pendência |
| `reindexar` | **Troca de modelo ou de dimensão**: para cada alerta elegível, vetoriza todos os trechos com o modelo e a dimensão configurados e, **só depois de o alerta ficar completo**, apaga os vetores dos outros modelos e dimensões; mostra o andamento por alerta e um resumo (alertas refeitos, trechos novos, vetores antigos apagados, falhas) | resumo | 0 sem falhas; 1 se algum alerta falhou (os vetores antigos desse alerta são mantidos); 2 uso errado ou configuração |
| `reindexar --manter-antigos` | Igual, sem apagar os vetores dos outros modelos (para comparar ou voltar atrás) | idem | idem |

`indexar --tudo` refaz os trechos **do modelo configurado** (por exemplo, depois de mudar o fatiamento) sem mexer nos de outros modelos; `reindexar` é o comando da **troca de modelo**. `indexar --status` mostra, por modelo e dimensão, quantos trechos há e **avisa em destaque** quando o índice só tem vetores de outro modelo ou dimensão ("rode `reindexar`"), ou quando há alertas elegíveis sem vetores do modelo configurado.

Além disso: `coletar --alertas` e `reclassificar` **terminam chamando** a indexação (mesmo resumo no fim). `coletar --postos` e `--vistos` não.

## 5. Logs e privacidade

Logs do worker em JSON, como hoje (e no arquivo rotativo de produção). A indexação registra contagens, ids de alerta e erros de rede; **nunca** o texto dos alertas inteiro nem a chave. O `Embeddador` real não envia nada além do texto do trecho.

## 6. Testes exigidos

- fatiamento: cobertura, limites e a propriedade `texto[inicio:fim]` ≡ trecho;
- idempotência: duas passadas seguidas, a segunda não vetoriza nada;
- mudou o hash → só o alerta mudado é refeito;
- alerta removido → trechos apagados; e a consulta já não o devolve **antes** da passada (por causa do `JOIN`);
- trocou o modelo ou a dimensão → o varredor e o `reindexar` gravam os novos vetores ao lado dos antigos; a recuperação vetorial **só usa** o modelo e a dimensão configurados (teste com dois modelos de dimensões diferentes no mesmo banco, sem erro de comparação); enquanto um alerta não tem vetores do modelo novo, ele entra pela busca textual;
- `reindexar`: só apaga os vetores antigos de um alerta depois de o alerta ficar completo no modelo novo; falha em um alerta mantém os antigos dele; `--manter-antigos` não apaga nada; é idempotente;
- `indexar --status` avisa do modelo ou da dimensão diferentes;
- falha de embedding num alerta não apaga trechos bons nem derruba os outros;
- `vigor` muda sem reembedar;
- o agendador cria o job em outro executor e a coleta de postos não o atrasa (teste de configuração do agendador);
- `COLETAS_AUTOMATICAS=false` continua sem agendar nada.
