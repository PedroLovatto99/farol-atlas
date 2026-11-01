# Modelo de dados: chat de dúvidas de viagem (feature 003)

**Data**: 2026-11-01 | **Spec**: [spec.md](spec.md) | **Pesquisa**: [research.md](research.md)

O chat **não guarda conversa nenhuma no servidor** (FR-019, FR-030). O banco ganha só duas tabelas, ambas sem texto de pergunta, resposta ou IP: o **índice de trechos** (derivado dos alertas que o worker já coleta) e as **contagens anônimas** do uso. Tudo o mais deste documento (pergunta, conversa, resposta, citação, cartão) vive na memória do navegador ou na memória do processo durante uma requisição, e está descrito aqui só para o desenho ficar completo.

**Migração Alembic `0005_chat`** (a `0004` é a `versao_dados`): cria a extensão `vector`, as duas tabelas e os índices. Nenhuma tabela das features 001 e 002 muda. Descer (`downgrade`) remove as duas tabelas e deixa a extensão (outra coisa pode usá-la). O teste de migrações ganha as tabelas novas e continua conferindo que o esquema migrado bate com os modelos (`compare_metadata`).

---

## 1. Tabela `trecho_alerta` (índice de trechos)

Um trecho é um intervalo do texto de um alerta confirmado, com o vetor dele. Só existe para alertas que valem para o nível; é **derivado**: pode ser apagado e refeito a qualquer momento a partir de `alerta` (`python -m farol.worker indexar --tudo`).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | inteiro, chave primária | |
| `alerta_id` | inteiro, FK para `alerta.id` | `ON DELETE CASCADE`; índice |
| `alerta_hash` | texto (64) | O `confirmado_hash` do alerta no momento da indexação. **A consulta exige `trecho.alerta_hash = alerta.confirmado_hash`**: trecho de conteúdo antigo nunca é devolvido |
| `classificacao_id` | inteiro, FK para `classificacao.id` | A classificação vigente usada para `paises` (detecta reclassificação com o mesmo hash) |
| `posicao` | inteiro | Ordem do trecho dentro do alerta (0, 1, 2…) |
| `inicio`, `fim` | inteiros | Intervalo `[inicio, fim)` em `alerta.texto`. **O texto exibido no "Ver trecho" é `alerta.texto[inicio:fim]`, nunca uma cópia**, então é idêntico ao original (SC-002) |
| `paises` | `text[]` | Códigos dos territórios citados na classificação vigente (`nivel_territorio.territorio_codigo`). Vazio para alerta que não é de viagem. Índice GIN |
| `em_vigor_para` | `text[]` | Códigos dos territórios para os quais este alerta é o que rege o nível (vem do `mapa`, via `worker`). **Dica de ordenação e de filtro**; na hora da resposta a verdade é a ferramenta de nível (`define_nivel` do painel) |
| `modelo_embedding` | texto | Modelo que gerou o vetor. Ex.: `google_genai:gemini-embedding-001`. Parte da chave única: vetores de modelos diferentes do mesmo trecho podem coexistir durante a troca |
| `dimensoes` | inteiro | Dimensão com que este vetor foi gerado (padrão 768, de `EMBEDDINGS_DIMENSOES`) |
| `embedding` | `vector` (sem dimensão fixa na coluna) | Vetor do trecho (`task_type` de documento). `CHECK (vector_dims(embedding) = dimensoes)`. Sem índice vetorial (poucas centenas de linhas: varredura exata). **A consulta só compara linhas com `modelo_embedding` e `dimensoes` iguais aos configurados** |
| `indexado_em` | timestamptz | |

**Restrições**: único `(alerta_id, alerta_hash, modelo_embedding, dimensoes, posicao)`; `fim > inicio`; `dimensoes > 0` e `vector_dims(embedding) = dimensoes`. Trocar de modelo ou de dimensão **não exige migração**: o novo conjunto de vetores é gravado ao lado do antigo e o comando `reindexar` apaga o antigo depois.

**Estados e transições** (para cada alerta elegível; a elegibilidade usa as mesmas regras do nível: `confirmado_execucao_id` preenchido, `removido_em` nulo, página lida, classificação vigente `ok`):

```
sem trechos ──(varredor vetoriza)──► indexado (hash H, modelo M, classificação C)
indexado ──(hash muda)──────────────► sem trechos ──► reindexado (novo H)
indexado ──(classificação muda)─────► atualiza `paises`/`em_vigor_para` (sem reembedar)
indexado ──(modelo muda)────────────► sem trechos ──► reindexado (novo M)
indexado ──(alerta removido ou sem confirmação)──► trechos apagados
```

A consulta exclui imediatamente (por `JOIN`) o que saiu da lista ou mudou de hash, mesmo antes de o varredor apagar as linhas. Só a **entrada** depende do varredor (≤ 5 min + vetorização), e ela vem depois da coleta completa e da classificação, que são anteriores. Total dentro dos 15 minutos de FR-008.

**Consultas** (todas parametrizadas, sem SQL montado com texto da pessoa; número fixo de consultas por pergunta, sem N+1):
1. *Recuperar por similaridade*: trechos **do modelo e da dimensão configurados** (`WHERE modelo_embedding = :modelo AND dimensoes = :dimensoes`, antes do `ORDER BY`, para nunca comparar dimensões diferentes), com `JOIN alerta` (vigência), filtro opcional `paises && :codigos`, ordenados por `embedding <=> :vetor`, `LIMIT :k`. Traz `alerta_id`, `inicio`, `fim`, `distancia`. Alertas elegíveis **sem** nenhuma linha do modelo configurado entram pela consulta 2.
2. *Recuperar por texto* (plano B): o mesmo filtro, `to_tsvector('portuguese', substring(alerta.texto from inicio+1 for fim-inicio)) @@ plainto_tsquery('portuguese', :consulta)`, ordenado por `ts_rank`.
3. *Alertas citados*: um `SELECT` dos alertas (`titulo`, `url`, `publicado_em`, `modificado_em`, `texto`) pelos ids recuperados, para montar as citações e fatiar o texto.

## 2. Tabela `contagem_chat` (contagens anônimas, FR-030)

Um contador por dia e por tipo de evento. **Nada que identifique pessoa, pergunta ou resposta.**

| Coluna | Tipo | Regras |
|---|---|---|
| `dia` | data | **Dia em horário de Brasília** (`America/Sao_Paulo`) |
| `chave` | texto (40) | Uma das chaves abaixo |
| `valor` | inteiro, padrão 0 | `valor >= 0` |

Chave primária `(dia, chave)`.

| Chave | O que conta |
|---|---|
| `perguntas` | Perguntas processadas no dia. **É também o contador do teto global** (FR-026a): a reserva é `UPDATE … SET valor = valor + 1 WHERE valor < :teto RETURNING valor` (se não vier linha, o teto foi atingido); a devolução (falha por indisponibilidade ou estouro de tempo) é `valor = GREATEST(valor - 1, 0)` |
| `recusas` | Fora do escopo ou recomendação própria |
| `nao_encontrei` | Respostas "não encontrei nos dados" |
| `so_registros` | Respostas de contingência só com cartões |
| `pergunta_de_volta` | O chat perguntou de qual país se tratava |
| `limite_por_hora` | Tentativas barradas pelo limite por IP |
| `limite_do_dia` | Tentativas barradas pelo teto global |
| `falhas_servico` | Serviço de linguagem fora do ar ou sem cota |
| `erros_internos` | Falha do nosso código (ferramenta, banco, verificador); a pessoa vê a mesma mensagem de indisponível, com o código `erro_interno` |
| `estouros_de_tempo` | Passou de 20 s |
| `travas` | A trava do código descartou e refez uma resposta |
| `pais_invalido_pedido` | O modelo pediu uma ferramenta para país fora da lista do código |
| `ferramenta_recusada` | O modelo chamou uma ferramenta de lista com argumento fora do enum, ou uma de lista com país detectado |
| `ferramenta_nivel`, `ferramenta_visto`, `ferramenta_postos`, `ferramenta_alertas` | Uso de cada ferramenta |
| `ferramenta_lista_nivel`, `ferramenta_lista_visto`, `listas_truncadas` | Perguntas de lista (sem país específico) e quantas passaram de 50 nomes |

**Escrita sem tocar a versão dos dados.** As atualizações dessa tabela usam `abrir_sessao(..., versiona=False)` (parâmetro novo, padrão `True`), para não subir o contador de versão (`infra/versao.py`) e **não invalidar o cache de leitura** de `/mapa`, `/paises/{codigo}` e `/vistos` a cada pergunta. Teste: depois de N perguntas, a versão dos dados não mudou. A indexação (`trecho_alerta`) sobe a versão normalmente (é raro e acompanha mudança de alerta).

## 3. Estado só em memória do processo da API

- **Janela por IP**: para cada IP, a lista dos instantes das perguntas na última hora (estrutura `deque` por IP, descartando o que passou de 60 min; limpeza periódica de IPs sem registros). **Nunca vai a disco nem a log**; some no reinício, o que é aceitável (e é o que mantém o IP fora do banco, FR-026). Reserva e devolução de vaga como nos contadores do banco.
- **Rascunho da requisição**: a pergunta, o histórico, os artefatos das ferramentas e a resposta existem só durante a requisição e são descartados ao fim. Não entram em log nem em métrica.

## 4. Entidades da spec e onde cada uma mora

| Entidade (spec) | Onde | Observações |
|---|---|---|
| Pergunta | Corpo do `POST /chat`, memória da requisição | Até 500 caracteres |
| Conversa (sessão) | **Só no navegador** (`useChat`), em memória | Some ao recarregar; "Nova conversa" a apaga; as últimas 6 mensagens são reenviadas a cada pergunta |
| Resposta | Evento `resposta` do SSE | `texto` (prosa do modelo, só texto), `situacao`, `cartoes`, `citacoes`, `avisos` |
| Trecho de alerta | `trecho_alerta` (índice) + fatia de `alerta.texto` | |
| Alerta | `alerta` (001) | Sem mudança |
| Registro do sistema | Calculado na hora pelas funções do painel | Nível (`montar_painel`), visto (`montar_visto_do_pais`), postos (`montar_painel`) |
| Lista de países | Calculada na hora por `montar_mapa` (nível) e `montar_vistos_do_mapa` (visto), filtrada por país | Só países, em ordem alfabética, até 50 nomes e o total; os mesmos do filtro da legenda do mapa |
| Citação | Montada pelo código no pipeline | Ver abaixo |
| Limite de uso | Janela por IP (memória) + `contagem_chat.perguntas` (banco) | |
| Contagem anônima de uso | `contagem_chat` | |
| Pergunta-gabarito | `backend/tests/gabarito/chat/gabarito.yaml` | Arquivo versionado, não é tabela |

### Citação (valor, não tabela)

| Campo | Alerta | Registro |
|---|---|---|
| `tipo` | `alerta` | `nivel`, `visto` ou `postos` |
| `titulo` | Título do alerta | Nome da fonte (ex.: "Itamaraty, nível de alerta"; "Wikipédia, vistos"; "Postos") |
| `data` | `modificado_em` ou, na falta, `publicado_em` (001, FR-007b) | Data do dado, como o painel (atualização do nível; `dado_de` do visto; `conferido_em` dos postos) |
| `url` | Link oficial no gov.br | Link da fonte (artigo da Wikipédia, Portal Consular, página do posto) |
| `vigor` | `em_vigor` ou `anterior` (comparando com o alerta que rege o nível do país) | `nao_se_aplica` |
| `trecho` | `alerta.texto[inicio:fim]`, texto original, só do trecho usado | nulo |
| `licenca` | nulo | `CC BY-SA` para o visto |

### Cartão (valor, não tabela)

Reaproveita os DTOs da API que já existem, para o painel e o chat mostrarem **o mesmo valor com o mesmo texto**:
- `nivel`: país, `Nivel`, regiões (`Regiao`), `regiao_unica_do_alerta`, alerta que rege (título, data, link) e data da última atualização dos dados;
- `visto`: o DTO `Visto` do painel (categoria, permanência, RG, observações com tradução, fonte, data, `desatualizado`, `territorio_nome`);
- `postos`: `PostoNoPainel` (tipo, cidade, endereço, telefone de plantão, fonte e data), posto responsável e `sem_posto_indicado`.
- `lista`: o critério em texto legível (por exemplo, "Não viaje" ou "Isento, entrada com RG"), os países (`codigo` e `nome`), `total`, `exibidos`, `truncada` e a fonte e a data do dado (Itamaraty e última atualização dos dados; ou Wikipédia, CC BY-SA, fonte não oficial, e `coletado_em`), mais `desatualizado`.

## 5. Regras de validação que valem no servidor (Pydantic)

- `pergunta`: texto, 1 a 500 caracteres depois de `strip()`; sem caracteres de controle.
- `historico`: lista de 0 a 6 itens; cada item `{papel: "pessoa"|"assistente", texto: 1 a 1500 caracteres}`; um histórico com mais de 6 itens é recusado com 422 (o frontend nunca manda mais que 6).
- Códigos de país: só os que o `ResolvedorDePaises` conhece (`^[A-Z]{2,3}$` e existentes).
- Nada do corpo vai para o log. O `uvicorn` não registra corpo; os logs da aplicação do chat registram só códigos de evento.
