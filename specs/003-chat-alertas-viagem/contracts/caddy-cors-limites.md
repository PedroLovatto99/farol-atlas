# Contrato: Caddy, CORS e limites do chat

**Spec**: FR-025 a FR-031 | **Constituição**: princípio VIII | **Pesquisa**: [../research.md](../research.md) D8, D9

A única rota que não é de leitura é `POST /api/v1/chat`. Tudo o que muda na borda (Caddy, CORS, limites) vale **só para essa rota**; as demais ficam como estão.

## 1. Caddyfile (`deploy/Caddyfile`)

O `Caddyfile` da produção ganha um *snippet* com o `reverse_proxy` (para não duplicar os ajustes de IP, de saúde e de espera de reinício) e dois blocos `handle`. Esboço da estrutura, não o arquivo final:

```caddyfile
(api) {
	reverse_proxy api:8000 {
		header_up X-Forwarded-For {remote_host}
		header_up -X-Real-IP
		health_uri /api/v1/saude
		health_interval 5s
		health_timeout 2s
		health_passes 1
		health_fails 2
		lb_try_duration 10s
		lb_try_interval 250ms
		{args[0]}            # linhas extras de cada uso (ex.: flush_interval -1)
	}
}

{$DOMINIO} {
	header { … cabeçalhos de segurança, como hoje … }

	# Pergunta do chat: corpo até 16 KB, resposta em fluxo (sem compressão, sem buffer)
	handle /api/v1/chat {
		request_body { max_size 16KB }
		import api "flush_interval -1"
	}

	# Todo o resto: só GET na prática, corpo até 1 KB, compressão
	handle {
		encode zstd gzip
		request_body { max_size 1KB }
		import api ""
	}
}
```

- **Dimensionamento dos 16 KB**: pergunta de 500 caracteres + 3 respostas de histórico de até 1.500 + 3 perguntas de até 500, no pior caso de acentuação (2 bytes por caractere) + estrutura JSON ≈ **13 KB**. A validação exata é do Pydantic (campos com `max_length`); o Caddy só barra o exagero antes de chegar à API.
- **`flush_interval -1`**: o Caddy repassa cada evento assim que chega (o progresso aparece na hora). **Sem `encode`** nessa rota, para o fluxo não ser retido.
- **Tempos**: `write` do servidor segue em 30 s (acima dos 20 s do chat); `read_header` e `read_body` seguem em 10 s.
- **Sintaxe do snippet com argumento** (`{args[0]}`, `import api "…"`) **a validar no `caddy validate` do CI**; se não servir, usa-se um snippet por rota. A estrutura acima é a intenção, não a forma final.
- O HSTS, o `nosniff`, o `Referrer-Policy` e a CSP `default-src 'none'; frame-ancestors 'none'` continuam em todas as respostas.

**Mudanças em `ferramentas/verificar-caddy.sh`** (continua rodando no job `producao` do CI): POST de 2 KB em `/api/v1/mapa` → 413 (como hoje); POST de ~10 KB em `/api/v1/chat` → passa (a API de mentira responde 200); POST de ~20 KB em `/api/v1/chat` → 413; a resposta de `/chat` **não** é comprimida e os eventos chegam sem retenção (a API de mentira manda dois eventos espaçados; o teste confere o intervalo entre eles).

## 2. CORS por rota (`farol/api/app.py`)

Hoje: `allow_methods=["GET"]`, `allow_headers=[]`, sem credenciais, origens de `CORS_ORIGENS`. Passa a existir um **despachante fino** (middleware ASGI) que escolhe o `CORSMiddleware` pelo caminho:

| Caminho | Métodos | Cabeçalhos aceitos | Origens | Credenciais |
|---|---|---|---|---|
| `/api/v1/chat` | `POST` | `Content-Type` | as de `CORS_ORIGENS` | não |
| qualquer outro | `GET` | nenhum | as de `CORS_ORIGENS` | não |

Em desenvolvimento nada muda para as outras rotas. **Testes** (unidade, `TestClient`): preflight de `POST /chat` da origem permitida → 200 com `Access-Control-Allow-Methods: POST` e `Allow-Headers` com `Content-Type`; de origem não permitida → sem `Allow-Origin`; preflight de `POST /mapa` → continua recusado (400); `DELETE /chat` → recusado; resposta `429` e `200` do chat saem com `Access-Control-Allow-Origin` (o navegador precisa ler o `Retry-After`; o cabeçalho é exposto com `expose_headers=["Retry-After"]` no CORS do chat).

Os testes que hoje afirmam "POST não é permitido pelo CORS" (`test_cors_nao_libera_metodos_de_escrita`, os preflights de `test_app_producao.py`) **mudam de alvo**: continuam valendo para todas as rotas exceto `/chat`.

## 3. Limites do chat (`farol/api/chat/limites.py`, nome indicativo)

Sequência por requisição (cada passo só roda se o anterior passou):

1. **Validação do corpo** (Pydantic) → `422` se inválido. *Não conta.*
2. **Limite por IP**: janela deslizante de 60 minutos, 20 perguntas, na memória do processo, IP = `request.client.host` (o IP real que o `IpReal` já resolveu). Cheio → `429`, `codigo = limite_por_hora`, `Retry-After` e `espera_segundos` = tempo até a pergunta mais antiga da janela sair. *Reserva uma vaga.*
3. **Teto global do dia**: `contagem_chat.perguntas` do dia de Brasília; reserva atômica `UPDATE … WHERE valor < 500`. Sem vaga → devolve a vaga do IP, `429`, `codigo = limite_do_dia`, `volta_em` = 00:00 de Brasília do dia seguinte e `Retry-After` correspondente.
4. **Pipeline** (20 s). Em **sucesso, recusa, "não encontrei" ou pergunta de volta**, as vagas ficam gastas. Em **indisponibilidade do serviço de linguagem ou estouro de tempo**, as duas vagas são **devolvidas** (FR-026b), e `falhas_servico` ou `estouros_de_tempo` sobe.

Observações:
- Perguntas barradas pelo passo 2 ou 3 sobem `limite_por_hora` / `limite_do_dia` (contagens anônimas).
- O limite geral de 120 pedidos/min por IP (`LimiteDePedidos`) continua na frente de tudo e vale também para o chat.
- Nenhuma dessas estruturas guarda o texto da pergunta; a janela por IP guarda só instantes e some no reinício.
- As gravações de `contagem_chat` usam `abrir_sessao(..., versiona=False)` para não invalidar o cache de leitura.

## 4. Variáveis de ambiente (nomes reais, em `Configuracoes` e no `.env.example`)

| Variável | Padrão | Uso |
|---|---|---|
| `CHAT_HABILITADO` | `false` | `false` → `POST /chat` responde `503 chat_desligado`. Só é ligado depois dos limites (T133a). Com `AMBIENTE=producao` e o chat ligado, a partida falha se `CHAT_LIMITE_POR_HORA_POR_IP` ou `CHAT_LIMITE_POR_DIA` forem ≤ 0 |
| `CHAT_LIMITE_POR_HORA_POR_IP` | `20` | Passo 2 |
| `CHAT_LIMITE_POR_DIA` | `500` | Passo 3 |
| `CHAT_TEMPO_MAXIMO_SEGUNDOS` | `20` | Passo 4 |
| `CHAT_PERGUNTA_MAX_CARACTERES` | `500` | Validação (o contrato OpenAPI declara 500; mudar exige regenerar o contrato) |
| `CHAT_HISTORICO_MENSAGENS` | `6` | idem |
| `CHAT_TRECHOS_POR_PERGUNTA` | `4` | Recuperação |
| `LLM_CHAT`, `LLM_CHAT_ALTERNATIVO` | vazios | Modelo principal e alternativo (`provedor:modelo`); vazio = o do classificador |
| `GOOGLE_API_KEY_CHAT` | ausente | Chave de projeto próprio (cota isolada). Obrigatória com o chat ligado; nunca cai em `GOOGLE_API_KEY` (produção não parte sem ela) |
| `EMBEDDINGS_MODELO`, `EMBEDDINGS_DIMENSOES` | `google_genai:gemini-embedding-001`, `768` | Embeddings |
| `INDEXACAO_INTERVALO_MINUTOS` | `5` | Agenda do varredor |
| `LANGSMITH_TRACING` | fixo `false` no compose | Rastreamento externo desligado |

Nenhuma variável é obrigatória em produção; sem modelo, o chat entra em contingência. Todas as chaves são `SecretStr` e não aparecem em `repr`, log, resposta ou erro (os testes de segurança existentes ganham o chat).
