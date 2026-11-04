# Farol Atlas

## Sobre o Projeto

O **Farol Atlas** é um site pessoal e **não oficial** que mostra, num globo interativo, a situação de viagem de cada país para brasileiros. Ele reúne num só lugar os **alertas de viagem do Itamaraty**, os **requisitos de visto** e os **postos brasileiros no exterior**, informações que hoje estão espalhadas em muitas páginas.

Os dados são coletados do Portal Consular do Itamaraty e do artigo da Wikipédia "Visa requirements for Brazilian citizens" (CC BY-SA). Um **modelo de linguagem** classifica o nível de cada alerta, e o que não foi confirmado aparece como "não verificado", nunca como o estado mais favorável.

O site não substitui as fontes oficiais: antes de viajar, confirme sempre as informações no Portal Consular e com o consulado ou a embaixada do país.

---

## Funcionalidades

- Globo 3D com o nível de alerta de cada país: sem alerta, evite viagens não essenciais, não viaje e não verificado
- Destaque para regiões mais graves dentro de um país, com borda própria
- Modo "Vistos", que colore o globo pela situação de visto para brasileiros, incluindo os países que aceitam entrada com o RG
- Painel de cada país com nível, alertas, visto, embaixadas e consulados
- Ícones dos postos no mapa, com a ligação ao posto responsável nos países que não têm um
- Busca de países e filtros por nível ou por categoria de visto na legenda
- Chat que responde sobre o alerta e o visto de um país com os mesmos dados do painel; o modelo de linguagem, quando usado, só identifica o país e o assunto, e nunca escreve a resposta
- Modo daltonismo, com paleta própria em "Alertas", padrões no mapa e preferência guardada no navegador
- Interface adaptada para telas a partir de 360 px, com suporte a teclado e a movimento reduzido

---

## Tecnologias Utilizadas

* **Front-end:** TypeScript, React 19, Vite, Tailwind CSS, MapLibre GL JS
* **Back-end:** Python 3.13, FastAPI, SQLAlchemy, Alembic, APScheduler, Beautiful Soup
* **Banco de dados:** PostgreSQL 18
* **IA:** LangChain, com Google Gemini ou Ollama
* **Conteinerização:** Docker e Docker Compose
* **Testes e qualidade:** pytest, Vitest, Testing Library, Ruff, mypy, import-linter, ESLint, Prettier
* **CI:** GitHub Actions, com as verificações do backend e do frontend e a auditoria de dependências

---

## Instalação e Configuração

### 1. Pré-requisitos

- [Docker](https://www.docker.com/) com Compose v2
- Uma chave da [API do Gemini](https://ai.google.dev/) ou o [Ollama](https://ollama.com/) com um modelo local, para classificar os alertas

Para rodar sem Docker, você também vai precisar de:

- [uv](https://docs.astral.sh/uv/), que instala o Python 3.13
- [Node.js](https://nodejs.org/) 24
- [PostgreSQL](https://www.postgresql.org/) 18

### 2. Clonar o repositório

```bash
git clone https://github.com/PedroLovatto99/farol-atlas.git
cd farol-atlas
```

### 3. Configurar variáveis de ambiente (.env)

Copie o arquivo de exemplo e preencha os valores. O `.env.example` traz a lista completa, com as variáveis opcionais e as de produção.

```bash
cp .env.example .env
```

As principais para o ambiente de desenvolvimento são:

```ini
# Banco de dados
POSTGRES_USER=farol
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=farol
# Dentro do Docker, o host é "postgres"
DATABASE_URL=postgresql+psycopg://farol:sua_senha_aqui@postgres:5432/farol
# Banco dos testes do backend
DATABASE_URL_TESTE=postgresql+psycopg://farol:farol@127.0.0.1:5433/farol_teste

# API
CORS_ORIGENS=http://localhost:5173
API_DOCS_HABILITADA=true

# Coleta: contato que vai no User-Agent (URL ou e-mail)
CONTATO_COLETA=https://github.com/seu-usuario/seu-repositorio
PAUSA_SEGUNDOS=2
LIMITE_HORAS_PARTIDA=20
COLETAS_AUTOMATICAS=false

# Classificador de alertas, no formato "provedor:modelo"
LLM_CLASSIFICADOR=google_genai:nome-do-modelo
GOOGLE_API_KEY=sua_chave_aqui
# Ollama rodando na máquina, visto de dentro dos containers
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Endereço da API visto pelo navegador
VITE_API_URL=http://localhost:8000
```

**IMPORTANTE:** troque o `CONTATO_COLETA`. Com o valor de exemplo, o worker se recusa a coletar. Sem chave do Gemini e sem Ollama, tudo sobe, mas os alertas novos ficam pendentes de classificação.

### 4. Rodar com Docker (Recomendado)

```bash
docker compose up --build
```

Sobem o `postgres`, a `migracao` (aplica as migrações e o seed, depois termina), a `api`, o `worker` e o `frontend`.

### 5. Rodar sem Docker

Crie no PostgreSQL local um usuário e um banco com os mesmos valores do `.env`. Fora do Docker, o backend lê o `.env` da pasta `backend/`, então copie o arquivo para lá e troque o host do banco:

```bash
cd backend
cp ../.env .env
# no backend/.env: DATABASE_URL=postgresql+psycopg://farol:sua_senha_aqui@localhost:5432/farol
uv sync
uv run alembic upgrade head
uv run python -m farol.dominio.seed
```

Depois, rode cada serviço num terminal próprio:

```bash
# API (na pasta backend)
uv run uvicorn farol.api.app:criar_app --factory --reload --port 8000

# Worker de coleta (na pasta backend)
uv run python -m farol.worker

# Frontend (na pasta frontend)
npm ci
VITE_API_URL=http://localhost:8000 npm run dev
```

**IMPORTANTE:** o Vite não lê o `.env` da raiz, por isso o `VITE_API_URL` vai no comando. No PowerShell, use `$env:VITE_API_URL="http://localhost:8000"; npm run dev`. Se usar o Ollama, aponte o `OLLAMA_BASE_URL` para `http://localhost:11434`.

---

## Como Acessar

```bash
http://localhost:5173
```

Na primeira vez, todos os países aparecem como "não verificado", porque ainda não houve coleta. Para buscar os dados, rode:

```bash
docker compose exec worker python -m farol.worker coletar --alertas
docker compose exec worker python -m farol.worker coletar --vistos
docker compose exec worker python -m farol.worker coletar --postos
```

Sem Docker, use `uv run python -m farol.worker coletar --alertas` na pasta `backend`, e o mesmo para as outras opções.

**IMPORTANTE:** a coleta respeita o `robots.txt` e faz pausas entre as requisições, então a de postos demora.

A API fica em `http://localhost:8000`, com a saúde do serviço em `/api/v1/saude` e a documentação interativa em `/docs` (só com `API_DOCS_HABILITADA=true`).

Para rodar todas as verificações (lint, formato, tipos, testes e auditoria de dependências):

```bash
docker compose --profile teste up -d postgres-teste
cd backend && uv run poe verificar
cd ../frontend && npm run verificar
```

O guia para colocar o site no ar está em [docs/deploy.md](docs/deploy.md).

---

## Estrutura de Diretórios

```text
.
├── docker-compose.yml           # Desenvolvimento: postgres, migracao, api, worker, frontend
├── docker-compose.prod.yml      # Produção: API, worker, banco e Caddy
├── .env.example                 # Variáveis de ambiente (copiar para .env)
├── backend/                     # Python 3.13 + FastAPI
│   ├── Dockerfile               # Imagem única da API e do worker
│   ├── alembic/                 # Migrações do banco
│   ├── scripts/                 # Geração da geometria dos territórios
│   ├── src/farol/
│   │   ├── api/                 # Rotas, CORS, cache e limite de pedidos
│   │   ├── chat/                # Entende a pergunta e monta a resposta do chat
│   │   ├── classificacao/       # Classifica os alertas com o modelo de linguagem
│   │   ├── coleta/              # Leitura das páginas do Itamaraty
│   │   ├── dominio/             # Entidades e seed
│   │   ├── infra/               # Configuração, banco, HTTP e logs
│   │   ├── mapa/                # Dados do mapa e dos países
│   │   ├── vistos/              # Coleta e revisão dos vistos
│   │   └── worker/              # Agenda e comandos de coleta
│   └── tests/                   # Unidade, contrato e integração
├── frontend/                    # TypeScript + React + Vite
│   ├── public/geo/              # Geometria dos territórios
│   └── src/
│       ├── compartilhado/       # Tema, níveis, vistos e utilitários
│       ├── estado/              # Estado global da tela
│       ├── funcionalidades/     # Mapa, painel, legenda, busca, chat, vistos, daltonismo
│       ├── servicos/api/        # Cliente da API e tipos gerados do OpenAPI
│       └── testes/              # Mapa falso, API simulada e dados de exemplo
├── dados/                       # Seed: postos e territórios
├── deploy/                      # Configuração do Caddy
├── docs/                        # Guia de deploy
├── ferramentas/                 # Backup, testes de coleta e utilitários
├── prototipos/                  # Protótipos do mapa
├── specs/                       # Especificação, plano e tarefas de cada feature
└── .github/workflows/           # CI e auditoria de dependências
```
