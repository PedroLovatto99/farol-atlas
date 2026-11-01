# Contrato: interface do chat (frontend)

**Spec**: FR-014 a FR-019, FR-024 | **Pesquisa**: [../research.md](../research.md) D10 | **Tipos**: gerados de [openapi.yaml](openapi.yaml)

## 1. Componentes e responsabilidades (`frontend/src/funcionalidades/chat/`)

| Arquivo | Responsabilidade | Recebe |
|---|---|---|
| `BotaoDoChat.tsx` | Botão flutuante que abre o chat (`aria-expanded`, `aria-controls`); com o chat aberto vira o botão "Fechar chat" | `aberto`, `onAlternar`, posição derivada do estado do painel |
| `Chat.tsx` | Contêiner: painel (desktop) ou gaveta (celular), `role="dialog"` não modal, foco, `Esc`, aviso fixo, lista e caixa | `chat` (retorno de `useChat`), `modo` (`lateral`/`gaveta`) |
| `AvisoFixoDoChat.tsx` | O aviso do FR-016, sempre visível, com link do Portal Consular | nada |
| `ListaDeMensagens.tsx` / `MensagemDoChat.tsx` | Lista com `aria-live="polite"`, rola até o fim ao chegar resposta | mensagens |
| `Cartoes.tsx` | Cartões de nível, visto, postos e **lista de países** (nome, total, "mostrando os 50 primeiros", fonte e data; lista em `<ul>` com nome por extenso; o resto se vê na legenda do mapa) **reusando** os blocos do painel (`SecaoVisto`, `Posto`, o bloco de nível) com os DTOs do contrato | cartões |
| `Citacao.tsx` / `VerTrecho.tsx` | Citações; "Ver trecho" é um botão com `aria-expanded` que mostra o `trecho` como **texto** (nunca HTML), recolhido por padrão | citações |
| `CaixaDePergunta.tsx` | Campo (máx. 500 caracteres, contador acessível), enviar, **Nova conversa**; desabilitada enquanto espera | `onEnviar`, `situacao` |
| `useChat.ts` | Máquina de estados, histórico em memória, prazo de 20 s, consumo do SSE, tentar de novo | cliente do chat |
| `../../servicos/api/chat.ts` | `perguntarAoChat(corpo, sinal) → AsyncIterable<EventoDoChat>`: `fetch` POST + leitor de `ReadableStream` que decodifica o SSE e **valida cada evento** em tempo de execução | — |

Componentes **não chamam a API**; só `useChat` usa o serviço (constituição III).

## 2. Estado

- `Estado.chatAberto: boolean` no reducer (como `painelRecolhido`), ações `abrir-chat`, `fechar-chat`. Abrir/fechar o chat **não altera** `modo`, `niveisMarcados`, `vistosMarcados`, `selecionado`, `postosExpandidos`, `painelRecolhido` nem a câmera (teste de reducer: estado antes ≡ depois, exceto `chatAberto`).
- A conversa fica em `useChat`, montado em `Tela` (não dentro do chat), então **fechar o chat não apaga a conversa**; recarregar apaga. **Nada em `localStorage` nem `sessionStorage`.**
- Estados do `useChat`: `ocioso` → `enviando` (com `etapa` do último `progresso`) → `ocioso` (com a resposta) | `erro` (com `codigo` e se pode tentar de novo) | `limite` (com a espera ou a hora de volta). Em `enviando`, o botão enviar e o campo ficam desabilitados e o cancelamento por 20 s está armado.
- Histórico enviado: as últimas **6** mensagens (texto puro; para mensagens do assistente, só o `texto`, sem cartões nem citações), sem mensagens de erro ou de limite.

## 3. Convivência com o que já existe (FR-014, FR-015)

Layout atual: cabeçalho `absolute` no topo (z-10); legenda `absolute bottom-10 left-2` (z-10); painel do país `absolute` (z-20): `lateral` = coluna de 340 px à direita (`top-16 bottom-2 right-2`), `gaveta` = metade de baixo (`h-[55dvh]`); barra do painel recolhido = `top-16 right-2 w-[340px]` (desktop) ou `bottom-2 inset-x-2` (celular).

| Situação | Botão | Chat | Painel do país |
|---|---|---|---|
| Desktop, sem país selecionado | canto inferior direito (`bottom-2 right-2`) | painel `w-[380px]`, `top-16 bottom-2 right-2`, z-20 | — |
| Desktop, país selecionado, chat fechado | desloca-se para a esquerda da coluna de 340 px (`right-[calc(340px+1rem)]`) | — | como hoje |
| Desktop, país selecionado, **chat aberto** | vira "Fechar chat" | painel do chat na coluna da direita | **exibido como a barra compacta da 002**, acima do chat (estado `painelRecolhido` **inalterado**; só a apresentação muda); a barra continua tocável e, se a pessoa a expande, o chat é fechado |
| Celular, chat fechado | canto inferior direito, acima da gaveta/barra do painel (altura derivada do estado do painel) | — | como hoje |
| Celular, **chat aberto** | vira "Fechar chat" | gaveta inferior `h-[55dvh]` | exibido como barra no topo da gaveta (mesma regra: só apresentação) |

Invariantes testadas (Vitest + Testing Library):
- com o chat aberto, a linha de fonte de vistos, o aviso, a busca e o seletor de modo continuam no DOM, visíveis e focáveis (o chat não os cobre no desktop; no celular a gaveta cobre a legenda como a gaveta do painel já faz, e ela volta ao fechar);
- fechar o chat devolve o estado e a apresentação exatamente (instantâneo antes/depois);
- o `Esc`, com o foco dentro do chat, fecha o chat e não aciona o `verMundo` do painel; com um diálogo modal (Sobre, fronteiras) aberto, o `Esc` é do diálogo (a checagem de `[role="dialog"]` do `App.tsx` passa a ignorar o chat pelo atributo `data-chat`, já que ele é um diálogo não modal).

## 4. Acessibilidade e celular (FR-017)

- Foco: ao abrir, vai ao campo de pergunta; ao fechar, volta ao botão. Ordem de tabulação: lista (rolável com teclado) → "Ver trecho" → campo → Enviar → Nova conversa → Fechar.
- Leitor de tela: `aria-live="polite"` na lista; o progresso ("Buscando nos alertas…") é anunciado em uma região `role="status"`; erro e limite em `role="alert"`.
- Alvos de toque de 44 px (`min-h-11`); sem rolagem horizontal em 360 px; texto quebra (`break-words`); contraste AA com os tokens de cor atuais; informação nunca só por cor (o "anterior" e o "em vigor" têm texto).
- `prefers-reduced-motion`: sem transição de entrada/saída e sem rolagem suave (`useMovimentoReduzido` já existe).

## 5. Mensagens da interface (português; texto final fechado na implementação sob teste)

| Situação | Texto (referência) |
|---|---|
| Aviso fixo | "As respostas são geradas automaticamente a partir dos dados do site, não são orientação oficial e devem ser conferidas no Portal Consular. Não digite dados pessoais." |
| Progresso | "Identificando o país…", "Buscando nos alertas…", "Consultando o nível de alerta…", "Consultando o visto…", "Consultando os postos…", "Montando a resposta…" |
| Passou de 20 s | "A resposta está demorando mais que o normal." + botão **Tentar de novo** (a pergunta não conta nos limites) |
| Limite por hora | "Você chegou ao limite de 20 perguntas por hora. Tente de novo em N minutos." (a partir de `espera_segundos`) |
| Teto do dia | "O chat atingiu o limite de perguntas de hoje e volta amanhã, à meia-noite (horário de Brasília)." (a partir de `volta_em`) |
| Serviço fora | "O assistente está fora do ar agora. Os dados do site continuam disponíveis no mapa e no painel de cada país." |
| Chat desligado | "O chat está desligado no momento." |
| Alerta anterior | rótulo "Alerta anterior" na citação, com a data |

## 6. Testes exigidos (Vitest, comportamento, sem rede)

Abrir/fechar com teclado e mouse; foco indo e voltando; `Esc`; enviar e ver progresso; resposta com cartões, citações e "Ver trecho" abrindo/fechando; histórico limitado a 6 e sem cartões; 20 s de espera → aviso → tentar de novo; `429` com espera e com hora; `503`; evento `erro`; "Nova conversa"; recarregar apaga (nada em storage); layout nos dois modos do painel e do globo (reaproveitando o `mapa-falso`); sem `any`; nenhum HTML inserido (teste de segurança com texto de alerta contendo `<script>` e `<img onerror>`).
