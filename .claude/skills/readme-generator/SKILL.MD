---
name: readme-generator
description: Use esta skill sempre que o usuário pedir para criar, gerar, montar ou atualizar o README de um projeto (ex: "cria o readme desse projeto", "documenta esse repositório", "monta o readme", "escreve a doc inicial"). Cobre a investigação do código-fonte para descobrir stack, forma real de inicialização e estrutura de diretórios, e a montagem do README no formato fixo do usuário: título, sobre o projeto, funcionalidades, tecnologias utilizadas, instalação/configuração (com e sem Docker), como acessar e estrutura de diretórios comentada — sem uso de emojis, seguindo as convenções visuais de Markdown (separadores, negrito, blocos de código) que o usuário costuma usar.
---

# Readme Generator

Skill para gerar o README de um projeto sempre na mesma estrutura e estilo visual, investigando o código real em vez de inventar informação.

## Checklist rápido

1. Investigar o projeto (arquivos de dependências, Dockerfile, .env, scripts de start) antes de escrever qualquer seção sobre stack ou instalação.
2. Perguntar ao usuário o que não pode ser inferido do código (descrição/propósito do projeto, funcionalidades que ele quer destacar).
3. Montar o README seguindo a estrutura fixa de seções, na ordem definida abaixo — sem usar emojis em nenhum lugar do documento.
4. Seguir as convenções visuais (separadores `---`, negrito, blocos de código, callouts de aviso).
5. Gerar a estrutura de diretórios real do projeto (comentada), depois da seção "Como Acessar".
6. Revisar a acentuação e a cedilha do texto em português antes de finalizar (mesma atenção usada na skill de commit).

---

## 1. Investigar o projeto antes de escrever

Nunca escreva a seção de tecnologias ou de instalação de memória/suposição. Investigue o repositório primeiro:

- **Dependências/linguagem:** procure por `package.json`, `requirements.txt`, `pyproject.toml`, `Pipfile`, `go.mod`, `pom.xml`, `composer.json`, `Gemfile`, etc. Isso indica a stack real (front-end, back-end, bibliotecas de IA, etc.).
- **Containerização:** procure por `Dockerfile` e `docker-compose.yml`/`compose.yaml`. Se existirem, veja quais serviços estão definidos (app, banco de dados, cache) para descrever a seção Docker com precisão.
- **Variáveis de ambiente:** procure por `.env.example`, `.env.sample`, ou variáveis referenciadas diretamente no código (`os.getenv`, `process.env`, `os.environ`, etc.) para montar a lista real de variáveis — nunca invente nomes de variável.
- **Comando real de inicialização:** veja a seção `scripts` de um `package.json`, um `Makefile`, ou o entrypoint do projeto (`main.py`, `app.py`, `manage.py`, `index.js`) para saber o comando exato de start e a porta usada.
- **Banco de dados:** veja configs de conexão (ex: `settings.py`, `database.yml`, variáveis `DB_*`) para saber qual banco é usado.

Se o projeto só tiver suporte via Docker (sem instruções claras de setup manual) ou só tiver setup manual (sem Dockerfile), não force a existência da outra opção — sinalize isso ao usuário ao invés de inventar um caminho que o projeto não suporta.

Nunca copie valores reais de um `.env` existente no repositório para o README — use sempre placeholders (`sua_chave_aqui`, `nome_do_banco`, etc.), mesmo que o valor real esteja visível no código.

---

## 2. Perguntar o que não pode ser inferido do código

Algumas partes do README dependem de contexto que não está no código-fonte. Pergunte ao usuário:

- Uma descrição breve do propósito/ideia do projeto (o "porquê"), caso não fique óbvio pelo código ou por um README antigo.
- Funcionalidades que ele quer destacar como prioridade (o código pode sugerir algumas, mas confirme com o usuário antes de listar como "funcionalidade principal").
- Se o projeto tem algum tom/tema específico (como o exemplo do Fallout) que deveria influenciar o estilo do texto, ou se prefere algo mais neutro/corporativo. Isso não afeta emojis (esta skill nunca usa emojis), só o tom da escrita.

---

## 3. Estrutura fixa do README

Sempre monte o README seguindo esta ordem de seções, sem usar emoji em nenhum título, texto ou callout — nem no título do projeto:

```markdown
# <Nome do Projeto>

## Sobre o Projeto
<1 a 3 parágrafos explicando o que é o projeto, para quem é e o problema que resolve.
Destaque tecnologias e conceitos-chave em **negrito** dentro do texto.>

---

## Funcionalidades
- <funcionalidade 1>
- <funcionalidade 2>
- <funcionalidade 3>

---

## Tecnologias Utilizadas
* **Front-end:** <tecnologias, se houver>
* **Back-end:** <tecnologias, se houver>
* **Banco de dados:** <tecnologia, se houver>
* **IA:** <bibliotecas/serviços, se houver>
* **Conteinerização:** <Docker etc., se houver>

---

## Instalação e Configuração

### 1. Pré-requisitos
- <ferramentas necessárias, com link para cada uma>

### 2. Clonar o repositório
\`\`\`bash
git clone <url-do-repo>
cd <pasta-do-projeto>
\`\`\`

### 3. Configurar variáveis de ambiente (.env)
<explicação breve + bloco de código com cada variável comentada, com valores placeholder>

### 4. Rodar com Docker (Recomendado)
\`\`\`bash
docker-compose up --build
\`\`\`
<callout "IMPORTANTE:" se o processo for lento ou exigir atenção especial>

### 5. Rodar sem Docker
<passo a passo manual: instalar dependências, configurar serviços locais, comando de start>

---

## Como Acessar
\`\`\`bash
http://localhost:<porta>
\`\`\`
<instrução adicional, se houver algo específico para começar a usar>

---

## Estrutura de Diretórios
<árvore de diretórios real do projeto, comentada — ver seção "Estrutura de diretórios" abaixo>
```

Só inclua a subseção 4 (Docker) e/ou a 5 (sem Docker) de acordo com o que o projeto de fato suporta — nunca as duas por padrão sem checar. Se só uma delas se aplica, remova o número da outra e renumere a sequência.

### Estrutura de diretórios

A árvore de diretórios vem sempre depois de "Como Acessar", como a última seção do README. Regras para montá-la:

- **Gere a árvore a partir do projeto real** (liste os diretórios/arquivos de fato presentes — nunca uma estrutura genérica de "como costuma ser" esse tipo de projeto).
- Use os caracteres de árvore (`├──`, `└──`, `│`) no mesmo estilo do exemplo abaixo, dentro de um bloco de código (sem especificar linguagem, ou usando \`\`\`text).
- Comente com `#` as pastas e arquivos que merecem explicação — não precisa comentar todo arquivo, só o que ajuda quem está lendo a se orientar (arquivo de orquestração, pasta de configuração, camadas da aplicação, pasta de testes, migrations, etc.). Alinhe os comentários quando possível, para ficar legível.
- Omita pastas irrelevantes para quem vai ler o README: `node_modules/`, `.git/`, `venv/`, `__pycache__/`, `dist/`, `build/`, artefatos de compilação, e qualquer coisa gerada automaticamente que não ajuda a entender a arquitetura.
- Se o projeto for muito grande, não é preciso listar cada arquivo individual dentro de uma pasta com muitos itens do mesmo tipo — agrupe com uma linha de comentário explicando o padrão (ex: `# Endpoints REST + GlobalExceptionHandler` ao lado da pasta `controller/`, em vez de listar arquivo por arquivo).

**Exemplo de referência do nível de detalhe esperado:**

```text
.
├── docker-compose.yml          # Orquestração: backend, frontend, postgres, redis
├── .env.example                 # Variáveis de ambiente exigidas (copiar para .env)
└── src/
    ├── backend/                 # Java 21 + Spring Boot
    │   ├── Dockerfile           # Multi-stage (build Maven → runtime JRE)
    │   └── src/main/java/com/exemplo/
    │       ├── controller/      # Endpoints REST
    │       ├── entity/          # Entidades JPA
    │       └── service/         # Regras de negócio
    └── frontend/                # React + TypeScript + Vite
        └── src/
            ├── components/      # Componentes reutilizáveis
            └── pages/           # Composição das telas (rotas)
```

### Sobre as convenções visuais

- Separador `---` entre as seções principais (`##`), nunca entre subseções (`###`).
- Negrito (`**termo**`) para destacar tecnologias, papéis ou termos-chave dentro de parágrafos.
- Lista de stack no formato `* **Categoria:** tecnologia, tecnologia`, só com as categorias que realmente existem no projeto (não force "Front-end" se o projeto é só um script de back-end, por exemplo).
- Subseções numeradas (`### 1.`, `### 2.`...) dentro de "Instalação e Configuração".
- Blocos de código sempre com a linguagem correta (` ```bash `, ` ```ini `, ` ```env `, etc.).
- Links markdown para qualquer ferramenta externa citada (ex: `[Docker](https://www.docker.com/)`).
- Callout de atenção no formato `**IMPORTANTE:** <texto>` (sem emoji) quando algo pode demorar, exigir configuração extra, ou for fácil de esquecer.
- Nenhum emoji em nenhum ponto do documento — nem no título, nem nos cabeçalhos de seção, nem nos callouts.

---

## 4. Revisão final

Antes de entregar o README:

- Releia a mensagem procurando por acentos ou cedilhas faltando (erros comuns: "nao" em vez de "não", "instalacao" em vez de "instalação", "configuracao" em vez de "configuração").
- Confirme que todo comando de instalação/execução presente no README foi de fato verificado no código (Dockerfile, scripts, Makefile) — nunca um comando genérico "de exemplo" que não corresponde ao projeto real.
- Confirme que nenhum valor real de `.env`/segredo do repositório foi copiado para o README.

## Casos especiais

- **Projeto sem Docker**: omita a subseção de Docker e explique só o setup manual.
- **Projeto que só roda via Docker** (múltiplos serviços interdependentes, por exemplo): avise o usuário que o setup manual não é trivial nesse caso e confirme se ele quer mesmo que essa seção seja escrita.
- **README já existente**: leia o conteúdo atual antes de sobrescrever, para não perder informações específicas (como troubleshooting customizado) que não seriam recriadas automaticamente.
- **Monorepo com múltiplos serviços**: confirme com o usuário se ele quer um README único cobrindo tudo ou um por serviço, antes de montar a estrutura.
- **Árvore de diretórios muito extensa**: priorize profundidade que ainda seja legível (geralmente 2-3 níveis) e agrupe/resuma pastas com muitos arquivos repetitivos, em vez de gerar uma árvore gigante que ninguém vai ler.