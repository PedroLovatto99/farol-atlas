<!--
Relatório de Impacto da Sincronização
- Mudança de versão: 1.0.0 → 1.0.1 (PATCH: esclarecimentos sem mudar a intenção dos princípios)
- Princípio III, dois esclarecimentos:
  1. a proibição de o backend gerar HTML não se aplica à documentação automática da API em
     desenvolvimento (desligada em produção);
  2. "não fazer uma requisição por país" vale para o carregamento do mapa; uma requisição
     quando o usuário seleciona um país é permitida.
- Seções adicionadas/removidas: nenhuma
- Modelos: nenhuma mudança necessária (plan-template, spec-template e tasks-template seguem válidos)
- TODOs pendentes: nenhum
- Histórico: 1.0.0 (2026-10-22) criou os princípios I a VIII, Idioma e Convenções e Governança;
  tornou os testes obrigatórios no tasks-template.
-->
# Constituição do Farol Atlas

Site pessoal e **não oficial** que mostra num mapa-múndi a situação de viagem de cada país para
brasileiros, a partir dos alertas do Itamaraty, com um chat que responde perguntas sobre esses
alertas. Backend em Python (FastAPI); frontend em TypeScript (React + Vite). Bibliotecas e versões
são definidas no plano.

As palavras MUST, MUST NOT e SHOULD seguem a RFC 2119.

## Princípios Fundamentais

### I. Qualidade verificada por ferramenta

- Todo código Python MUST ter type hints; lint, formatação e checagem de tipos MUST passar sem erros.
- O TypeScript MUST usar `strict: true`. `any`, implícito ou explícito, MUST NOT ser usado; usar
  `unknown` e validar.
- Nenhuma mudança MUST ser aceita se lint, tipos ou testes falharem.

**Justificativa**: ferramentas pegam defeitos de forma barata e igual para todos; revisão humana
não é o filtro principal.

### II. Testes antes do código (TDD)

- Toda regra de negócio, rota da API e extração de dados MUST começar por um teste que falha.
- Testes MUST NOT acessar a internet: páginas do gov.br vêm de arquivos salvos e o LLM é
  substituído por um modelo falso.
- Na interface, testes MUST verificar comportamento (o que o usuário vê e faz), não aparência.

**Justificativa**: a coleta depende de páginas externas instáveis; testes determinísticos e
offline são a única forma de detectar regressões na extração.

### III. Arquitetura

**Backend**
- MUST ser um monolito modular organizado por domínio. Um módulo MUST importar apenas a interface
  pública de módulos das camadas abaixo dele, e isso MUST ser conferido automaticamente.
- Cada responsabilidade MUST ter sua camada: rotas (controllers) recebem a requisição e devolvem a
  resposta; serviços contêm as regras de negócio e não conhecem HTTP; repositórios são os únicos
  que acessam o banco; a configuração do banco MUST ficar num único lugar.
- Rotas MUST NOT acessar o banco nem conter regra de negócio.
- Entradas e saídas da API MUST ser DTOs Pydantic; nenhuma rota devolve objetos do banco. Os tipos
  do frontend MUST ser gerados a partir do OpenAPI da API.
- O backend MUST devolver apenas JSON e MUST NOT gerar HTML nem CSS. Ler HTML na coleta é permitido.
  A documentação automática da API (ex.: `/docs` e `/redoc`) não conta como HTML gerado pelo
  backend, desde que seja habilitada só em desenvolvimento, por variável de ambiente, e fique
  desabilitada em produção.
- Consultas que devolvem listas MUST carregar os relacionamentos de uma vez (sem N+1: nunca uma
  consulta por item dentro de um laço). Rotas de lista MUST ter teste que limita o número de
  consultas ao banco.

**Frontend**
- MUST ser organizado por funcionalidade (mapa, painel, chat), com componentes pequenos e de
  responsabilidade única.
- Componentes MUST NOT conter regra de negócio nem chamar a API diretamente: recebem dados prontos
  por props, vindos de hooks ou serviços.
- No carregamento, o mapa MUST receber seus dados numa única chamada e MUST NOT fazer uma
  requisição por país. Uma requisição quando o usuário seleciona um país (ex.: os detalhes do
  painel) é permitida.
- A biblioteca do mapa MUST ficar isolada atrás de uma interface própria; trocá-la não pode exigir
  mudança em outros componentes.

**Justificativa**: fronteiras claras mantêm o projeto pequeno, testável e fácil de trocar peças
(banco, biblioteca de mapa) sem reescrever o resto.

### IV. Coleta responsável

- A coleta MUST respeitar o `robots.txt`, usar User-Agent honesto com contato e pausar entre
  requisições.
- A coleta MUST NOT contornar CAPTCHA, verificação humana ou bloqueio; se acontecer, MUST parar e
  registrar o motivo.

**Justificativa**: o projeto depende da boa vontade de sites públicos e não pode sobrecarregá-los
nem burlar suas proteções.

### V. Informação confiável

- Sem dado confirmado, o sistema MUST mostrar "não verificado" e MUST NOT mostrar o estado mais
  favorável.
- Toda informação exibida MUST mostrar a fonte e a data da coleta, e o site MUST avisar que não é
  oficial.
- O chat MUST responder apenas com base nos documentos coletados, citar as fontes e dizer quando
  não sabe.

**Justificativa**: decisões de viagem têm risco real; um falso "tudo bem" é pior que admitir
incerteza.

### VI. Acessível e pensado para o celular

- Toda tela MUST funcionar no celular.
- Cor MUST NOT ser a única forma de transmitir informação; usar também texto, legenda ou ícone.
- A interface MUST respeitar `prefers-reduced-motion`.

**Justificativa**: o mapa depende fortemente de cor e animação, e o acesso é majoritariamente
móvel.

### VII. Simples e gratuito de operar

- O sistema inteiro MUST subir com `docker compose`.
- MUST usar apenas serviços com plano gratuito; nenhuma dependência paga é obrigatória.
- O modelo de LLM MUST ser configurável, e o chat MUST continuar respondendo se o provedor
  principal falhar.

**Justificativa**: é um projeto pessoal sem orçamento; operar barato e sem dependência de um único
fornecedor garante que continue no ar.

### VIII. Segurança

- Chaves e senhas MUST ficar apenas em variáveis de ambiente do servidor, nunca no repositório nem
  no frontend. Toda chamada ao LLM MUST sair do backend.
- Rotas públicas MUST ser de leitura, exceto a pergunta do chat. Qualquer rota que altere dados
  (como a futura administração) MUST exigir autenticação.
- O chat MUST ter limite de perguntas por IP, tamanho máximo de pergunta e tempo máximo de resposta.
- Toda entrada MUST ser validada com Pydantic. Consultas ao banco MUST usar parâmetros; MUST NOT
  montar SQL com texto do usuário.
- Textos externos (alertas coletados, Wikipédia, respostas do LLM) MUST ser tratados como dados: o
  frontend MUST NOT inseri-los como HTML sem sanitizar, e o chat MUST NOT seguir instruções contidas
  neles.
- O CORS MUST aceitar apenas o domínio do frontend. Banco e Chroma MUST NOT ficar expostos na
  internet, apenas na rede interna do Docker.
- Dados pessoais MUST ser limitados ao necessário: perguntas do chat MUST NOT ficar associadas ao IP
  de quem perguntou.
- As dependências MUST ser conferidas contra vulnerabilidades conhecidas a cada mudança.

**Justificativa**: o chat é público e repassa texto externo a um LLM; sem essas barreiras, abre-se
espaço para abuso, vazamento de chaves e injeção de instruções.

## Idioma e Convenções

Interface, documentação, comentários e nomes no código MUST ser em português. Termos técnicos
consagrados podem ficar em inglês.

## Governança

- Esta constituição prevalece sobre outras práticas do projeto. Planos (`plan.md`) MUST passar pelo
  "Constitution Check" contra estes princípios; qualquer violação MUST ser justificada na tabela de
  Complexity Tracking.
- Emendas exigem alteração deste arquivo, atualização do Relatório de Impacto e propagação aos
  modelos em `.specify/templates/`.
- Versionamento semântico: MAJOR para remoção ou redefinição incompatível de princípio; MINOR para
  novo princípio ou ampliação material; PATCH para esclarecimentos e correções de redação.
- Toda revisão de mudança MUST verificar a conformidade com os princípios acima.

**Versão**: 1.0.1 | **Ratificada em**: 2026-10-22 | **Última emenda**: 2026-10-23
