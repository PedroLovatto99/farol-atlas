# Research: Chat do alerta e do visto

Decisões curtas. Nenhuma dependência nova; nada novo no banco.

## D1. Onde mora o chat e de onde vêm os dados

- **Decisão:** módulo novo `farol.chat`, na camada de `mapa`, `coleta`, `classificacao` e `vistos`,
  sem importá-los. Ele declara dois `Protocol` (`FonteDoPainel`, `ModeloDeEntendimento`) e
  dataclasses próprias de entrada. A `api` (`api/composicao.py`) implementa a `FonteDoPainel`
  chamando as mesmas funções do painel: `montar_mapa` (nomes para reconhecer o país, data e
  "desatualizado" do alerta) e `montar_painel_com_visto` (painel e visto do país).
- **Por quê:** paridade com o painel por construção (SC-001) e nenhuma regra repetida; os
  contratos do import-linter continuam valendo com `farol.chat` acrescentado.
- **Alternativa descartada:** o chat importar `mapa` e `vistos` (quebra o contrato de independência).

## D2. Os dados chegam como as visões do painel, e o chat não as importa

- **Decisão:** o `Protocol` devolve `VisaoDoPainel` e `VisaoDoVisto` "por formato": o chat declara
  `Protocol`s só com os atributos que lê (nível, regiões, alertas, observação, situação, fonte…), e
  as dataclasses do `mapa` e do `vistos` os satisfazem sem conversão (tipagem estrutural, conferida
  pelo mypy). Os membros dos `Protocol`s são `@property` (só leitura, covariantes):
  assim os `StrEnum` do `mapa` e do `vistos` são aceitos como `str` e as tuplas como `Sequence`.
- **Por quê:** zero código de conversão e o mypy pega qualquer divergência de campo.

## D3. Entendimento da pergunta: código primeiro, modelo só se o código não entender

Ordem (função pura `entender(pergunta, nomes)` em `chat/entendimento.py`):

1. Normaliza (NFKD sem acento, minúsculas, pontuação vira espaço), como `normalizar` da busca.
2. **Países:** procura, por palavra inteira e do nome mais longo para o mais curto, os nomes que a
   busca do site usa (`nome` sem o "(soberano)", `rotulo_busca`, `termos_busca` de `/mapa`) mais
   `chat/apelidos.yaml` (ex.: "eua" → US, "estados unidos" → US, "inglaterra" → GB, "holanda" → NL)
   e os **ambíguos** ("congo" → CG|CD, "guine" → GN|GW|GQ, "coreia" → KR|KP). Um trecho já casado
   não casa de novo ("guine-bissau" não vira também "guine"). Cada entrada do YAML tem teste e o
   código do território é conferido contra a lista de `/mapa` ao carregar.
3. **Brasil:** sozinho → `brasil`; ao lado de outro país → ignorado (FR-017).
4. **Assunto**, por palavras: fora do assunto vence ("embaixada", "consulado", "posto", "capital",
   "moeda", "idioma", "clima", "recomenda", "quais paises", "lista"); depois alerta ("alerta",
   "seguro", "seguranca", "perigo", "risco", "guerra", "viajar") e visto ("visto", "visa",
   "passaporte", "rg", "documento", "entrar", "entrada", "permanencia").
5. Sem palavra de assunto e sem sobra (só o país, conectivos e verbos como "fala", "sobre", "e",
   "como esta") → `alerta_e_visto` (FR-004).
6. **O código entendeu** quando achou ao menos um país (ou ambíguo, ou Brasil) e um assunto (ou
   nenhuma sobra). Só então responde sem modelo.
7. **Senão**, uma chamada ao modelo (D4). País vindo do código vale mais que o do modelo. Sem
   modelo (`LLM_CHAT` vazia) ou com falha: país achado pelo código → `alerta_e_visto`; sem país →
   `reformular` (FR-029).

- **Por quê:** a maioria das perguntas cita o país pelo nome; assim o modelo raramente é chamado
  (cota, FR-030) e o chat responde com o modelo fora do ar (FR-029).

Ajustes da revisão: país logo depois de uma palavra desconhecida ("Novo México", "Nova Jersey") não
vale, e a pergunta vai ao modelo ou recebe `reformular`; "Geórgia" sozinha pergunta de volta (país ou
estado americano); "seguro viagem" é fora do assunto, e "seguro" sozinho continua sendo alerta. A
lista enviada ao modelo usa `rotulo_busca` para Kosovo e Malvinas, que têm o `nome` do soberano.

## D4. A chamada ao modelo

- **Decisão:** `chat/modelo_langchain.py`, igual ao classificador: `init_chat_model(LLM_CHAT,
  **argumentos_do_modelo(...))` + `with_structured_output(PerguntaEntendida)`. Esquema Pydantic:
  `codigos: list[str]` (máx. 5) e `assunto: Literal["alerta", "visto", "alerta_e_visto",
  "fora_do_assunto"]`. O prompt traz a lista "código: nome" (como o classificador) e a pergunta
  entre delimitadores neutralizados (`<<<`/`>>>`).
- **Validação (FR-002):** códigos fora da lista são descartados; resposta que não passa no esquema,
  exceção ou tempo esgotado = "o modelo não respondeu" → `reformular` (ou a resposta do código, se
  ele achou o país). Só o nome da classe da exceção vai ao log, nunca a pergunta.
- **Tempo:** `argumentos_do_modelo` ganha o parâmetro opcional `tempo_limite_segundos` (padrão o
  atual, 90); o chat passa 10 e `max_retries=0`, porque a API do Google recusa com 400 qualquer
  prazo menor que 10 s (visto no teste com a chave real). Os 5 s do FR-029 ficam no `entender`, que
  roda a chamada numa thread e espera no máximo 5 s; isso vale para qualquer provedor. Chamada que
  estourou o prazo ainda na fila é cancelada. A sessão do banco é confirmada antes do modelo, para
  a conexão não ficar presa durante a espera. No Google, `thinking_level=minimal`: a mediana caiu de
  4,2 s para 2,0 s, com os mesmos acertos (8 chamadas por configuração).
- **O modelo nunca escreve a resposta:** o que ele devolve só escolhe o tipo e o país; o texto vem
  sempre de `textos.py`.

## D5. Cota: o chat não compromete a classificação (FR-030)

- `LLM_CHAT` própria. **Vazia = chat sem modelo** (só o código entende; nenhuma cota usada). A
  configuração **recusa** `LLM_CHAT` igual a `LLM_CLASSIFICADOR` (erro ao subir), porque no plano
  gratuito do Gemini a cota é por modelo e projeto: com outro modelo, o chat gasta outra cota.
- O chat roda no processo da `api`; a classificação, no `worker`. Não há fila nem conexão
  compartilhada, então o chat não atrasa a classificação.
- O gasto do chat é limitado em duas camadas: 20 perguntas/h por IP e modelo só quando o código não
  entende. Falha do modelo do chat só gera `reformular`; a coleta e a classificação não são tocadas.

## D6. Limite por IP

- **Decisão:** reaproveitar `BaldeDeFichas` (`api/limite.py`) com rajada = 20 e reposição de 20 por
  hora (uma ficha a cada 3 min); `por_minuto` passa a aceitar `float`. Chave = `request.client.host`,
  que o `IpReal` já trocou pelo IP do visitante. A rota gasta a ficha **depois** da validação do
  corpo (pergunta inválida não conta) e devolve 429 com `Retry-After` e o texto fixo.
- **Limite conhecido:** o balde garante que a 21ª pergunta seguida é barrada (SC-004), mas quem
  espaça as perguntas consegue até ~40 na primeira hora (rajada + reposição). Aceito: o objetivo é
  conter abuso e cota, e não precisa de estrutura nova.
- A contagem fica em memória (perdida no reinício, aceito na spec) e só guarda IP → fichas, nunca
  a pergunta (FR-028). O limite geral de pedidos (`LimiteDePedidos`) continua valendo por cima.

## D7. CORS só para a rota do chat

- **Decisão:** um middleware pequeno `CorsPorCaminho` (em `api/app.py`) com dois `CORSMiddleware`
  sobre o mesmo app: `/api/v1/chat` → `GET, POST` e cabeçalho `Content-Type`; o resto continua só
  `GET`, sem cabeçalhos. Mesmas origens (`CORS_ORIGENS`).

## D8. Tamanho da pergunta e o Caddy

- 300 caracteres em UTF-8 são no máximo ~1,2 KB só no pior caso (só caracteres de 4 bytes); com
  acentos do português ficam em ~600 bytes + `{"pergunta":""}`. O `max_size 1KB` do Caddy fica; o
  comentário "A API só tem GET" do Caddyfile é corrigido. Pergunta que o Caddy recusar (413) mostra
  a mensagem de falha genérica no frontend; o `maxLength=300` do campo evita isso no uso normal.

## D9. Nada guardado

- O corpo não é logado por ninguém (FastAPI e uvicorn não logam corpo). O chat não loga a pergunta;
  o `erro_inesperado` da `api` loga a exceção, então o chat captura as do modelo antes (D4). Um
  teste faz perguntas com um marcador e confere que ele não aparece em `caplog` (SC-007).
- POST não passa pelo `CacheDeLeitura` (só cacheia GET).

## D10. Frontend

- `funcionalidades/chat/`: `BotaoDoChat` (flutuante), `CaixaDoChat` (aviso fixo, mensagens,
  campo), `useChat` (estado local: mensagens e "respondendo"; some ao recarregar, FR-019) e
  `perguntarAoChat` no `servicos/api/cliente.ts`. Nada no `reducer` global: o chat não muda modo,
  seleção, filtros nem câmera (FR-020). Respostas renderizadas como texto do React; `url` só vira
  link se passar em `ehUrlWeb` (já existe). Mensagens anunciadas por `aria-live="polite"`.
