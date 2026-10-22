---
name: github-commit
description: Use esta skill sempre que o usuário pedir para fazer um commit, comitar alterações, subir/enviar código para o GitHub, dar um push, "salvar no git", ou qualquer variação disso — mesmo que não use a palavra exata "commit" (ex: "sobe isso pro repo", "salva essa mudança", "manda pro github"). Cobre o fluxo completo: analisar o que mudou, checar por segredos/credenciais antes de adicionar arquivos, descobrir/perguntar a URL do repositório remoto, montar a mensagem de commit no padrão Conventional Commits em português, e enviar (push) para o repositório remoto na branch atual.
---

# Github Commit

Skill para realizar commits de forma segura e padronizada em qualquer repositório Git, e enviá-los ao GitHub.

## Checklist rápido

1. Rodar `git status` e `git diff` para entender exatamente o que mudou.
2. Verificar se algum arquivo alterado parece conter segredos/credenciais. Se sim, **não** adicioná-lo sem confirmação explícita do usuário.
3. Descobrir a URL do repositório remoto (ver seção "Descobrindo a URL do repositório").
4. Adicionar (`git add`) apenas os arquivos relevantes para a mudança — nunca `git add -A` ou `git add .` às cegas.
5. Montar a mensagem de commit no formato definido abaixo, revisando a acentuação e a cedilha antes de finalizar.
6. Criar o commit.
7. Dar `git push` na branch atual.

Nunca use `--force`, `--no-verify` ou `--amend` neste fluxo, a menos que o usuário peça isso explicitamente na conversa (uma instrução antiga ou implícita não vale — precisa ser um pedido claro e atual).

---

## 1. Entender o que mudou

Antes de qualquer outra coisa, rode:

```bash
git status
git diff
```

Se já houver algo em stage de uma ação anterior, rode também `git diff --staged` para não ignorar essas mudanças na hora de escrever a mensagem de commit.

O objetivo aqui é ter clareza total do que está sendo alterado antes de decidir o que adicionar e como descrever a mudança — nunca escreva a mensagem de commit só com base no pedido do usuário, baseie-se no diff real.

Se `git status` mostrar que a árvore de trabalho está limpa (nada para commitar), avise o usuário e pare — não crie um commit vazio.

Se houver um merge em andamento com conflitos não resolvidos, não commite; avise o usuário que os conflitos precisam ser resolvidos primeiro.

---

## 2. Nunca commitar segredos

Antes de adicionar qualquer arquivo, verifique se ele se encaixa em padrões comuns de arquivos sensíveis, mesmo que o usuário não tenha mencionado nada sobre isso. Fique atento a:

- `.env`, `.env.local`, `.env.*` (exceto arquivos claramente de exemplo, como `.env.example` ou `.env.sample`)
- Chaves e certificados: `*.pem`, `*.key`, `*.crt`, `*.p12`, `*.pfx`, `id_rsa`, `id_ed25519`
- Arquivos de credenciais: `credentials.json`, `secrets.json`, `secrets.yml`/`.yaml`, pastas `.aws/`, `.ssh/`
- Arquivos de configuração de gerenciadores de pacote que costumam conter tokens: `.npmrc`, `.pypirc`
- Qualquer arquivo cujo nome contenha termos como `secret`, `token`, `password`, `apikey`, `credentials`

Além do nome do arquivo, dê uma olhada rápida no conteúdo do diff em busca de padrões típicos de segredo "vazado" dentro de um arquivo normal (ex: uma chave `AKIA...` da AWS, um bloco `-----BEGIN PRIVATE KEY-----`, ou uma variável como `API_KEY = "..."` com um valor longo e aleatório).

Se encontrar algo suspeito:
- **Não** inclua esse arquivo/trecho no `git add`.
- Avise o usuário claramente, apontando qual arquivo (e se possível qual trecho) parece sensível.
- Só inclua se o usuário confirmar explicitamente, depois de ver o aviso.

---

## 3. Descobrindo a URL do repositório remoto

Como esta skill é genérica e usada em vários projetos diferentes, a URL do repositório nunca deve estar fixa aqui. Em vez de depender de "é a primeira vez que o usuário pede um commit nesta conversa" (algo difícil de rastrear com confiabilidade), use o próprio estado do repositório Git, que já resolve isso naturalmente:

```bash
git remote -v
```

- **Se já existir um remote configurado** (geralmente chamado `origin`) — use-o diretamente. Não pergunte a URL de novo, mesmo que seja a primeira vez que você (a sessão atual) esteja fazendo um commit nesse projeto.
- **Se não existir nenhum remote** — pergunte ao usuário a URL do repositório antes de continuar, por exemplo: "Ainda não há um remote configurado neste repositório. Qual é a URL do repositório no GitHub? (ex: `https://github.com/usuario/repo.git`)". Depois de obter a resposta, configure o remote:

```bash
git remote add origin <url-informada>
```

- **Se existir mais de um remote** e não estiver claro qual usar, pergunte ao usuário qual deles é o destino do push, em vez de escolher por conta própria.

Esse método é o que torna a skill reutilizável entre projetos sem precisar guardar nenhuma URL fixa no arquivo.

---

## 4. Selecionando e adicionando arquivos

Adicione somente os arquivos relacionados à mudança lógica que está sendo commitada:

```bash
git add <arquivo1> <arquivo2> ...
```

Nunca use `git add -A` ou `git add .` de forma automática — isso arrisca incluir arquivos irrelevantes, temporários ou sensíveis que passaram despercebidos. A lista de arquivos deve vir da análise feita no passo 1 (e filtrada pelo passo 2).

Se o diff mostrar mudanças claramente não relacionadas entre si (por exemplo, uma feature nova misturada com uma reformatação de código em outro módulo sem relação), avalie sugerir ao usuário dividir em mais de um commit — mas sem travar o fluxo se ele preferir manter tudo junto.

---

## 5. Formato da mensagem de commit

Monte a mensagem sempre neste formato:

```
<tipo>: <mensagem curta em português>

<descrição mais detalhada em português, explicando o "porquê" do commit>
```

**Sobre o `<tipo>`**, escolha o que melhor representa a mudança real observada no diff — nunca use "feat" como padrão por preguiça de analisar:

| Tipo | Quando usar |
|---|---|
| `feat` | Uma nova funcionalidade ou capacidade foi adicionada |
| `fix` | Correção de um bug ou comportamento incorreto |
| `chore` | Tarefas de manutenção que não alteram lógica nem estilo (deps, configs, build) |
| `style` | Mudanças que não afetam o comportamento do código (formatação, espaçamento, ponto e vírgula) |
| `refactor` | Reestruturação de código sem mudar comportamento externo |
| `docs` | Mudanças apenas em documentação |
| `test` | Adição ou ajuste de testes |

**Sobre o título:** vai na primeira linha, no imperativo (ex: "adiciona validação de e-mail", não "adicionado" ou "adicionando"), sem ponto final.

**Sobre o corpo:** opcional em mudanças triviais (ex: um `chore` pequeno), mas recomendado na maioria dos casos. Foque em explicar *por que* a mudança foi feita — o contexto, o problema que resolve, a decisão por trás dela — e não em repetir o que o diff já mostra literalmente.

**Sobre acentuação:** escreva sempre em português correto e completo, com todos os acentos (á, é, í, ó, ú, â, ê, ô, ã, õ) e cedilha (ç) onde forem gramaticalmente necessários — nunca escreva a mensagem sem acentuar por automatismo. Isso vale tanto para o título quanto para o corpo. Antes de rodar o comando de commit, releia mentalmente a mensagem montada procurando especificamente por acentos ou cedilhas faltando (erros comuns: "nao" em vez de "não", "codigo" em vez de "código", "correcao" em vez de "correção", "funcao" em vez de "função") e corrija antes de prosseguir.

### Exemplos

**Exemplo 1**
```
fix: corrige validação de e-mail no formulário de cadastro

O regex anterior aceitava endereços sem domínio válido (ex: "user@"),
permitindo cadastros com e-mails inválidos. Ajustado para exigir
domínio com pelo menos um ponto.
```

**Exemplo 2**
```
refactor: extrai lógica de autenticação para módulo separado

O arquivo main.py estava concentrando rotas, lógica de negócio e
autenticação, dificultando manutenção. Nenhuma mudança de
comportamento — apenas reorganização.
```

**Exemplo 3**
```
chore: atualiza dependências do projeto para as versões mais recentes
```
(sem corpo — mudança trivial e autoexplicativa)

---

## 6. Criando o commit

Para preservar título e corpo como parágrafos separados de forma confiável, prefira um heredoc em vez de múltiplos `-m` quando o corpo tiver mais de uma linha:

```bash
git commit -F - <<'EOF'
<tipo>: <mensagem curta>

<corpo detalhado>
EOF
```

Para commits sem corpo, um único `-m` já resolve:

```bash
git commit -m "<tipo>: <mensagem curta>"
```

---

## 7. Enviando para o GitHub (push)

Descubra a branch atual:

```bash
git branch --show-current
```

Verifique se já existe upstream configurado para essa branch:

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u}
```

- Se o comando acima **funcionar** (já existe upstream), basta:
```bash
git push
```
- Se **falhar** (ainda não há upstream — comum no primeiro push da branch), configure o upstream ao empurrar, usando o remote identificado no passo 3:
```bash
git push -u origin <branch-atual>
```

---

## Regras rígidas

- Nunca use `--force` ou `--force-with-lease`.
- Nunca use `--no-verify` (isso pularia hooks de verificação, como linters ou checagens de segredo).
- Nunca use `--amend`.
- Essas três só podem ser usadas se o usuário pedir isso explicitamente, no turno atual da conversa — nunca por iniciativa própria, mesmo que pareça conveniente (ex: "corrigir" o commit anterior em vez de criar um novo).
- Nunca faça `git add -A` ou `git add .`.
- Nunca adicione um arquivo que pareça conter segredos sem confirmação explícita do usuário.

## Casos especiais

- **Diretório não é um repositório Git**: avise o usuário e pare, em vez de tentar `git init` por conta própria.
- **HEAD destacado (detached HEAD)**: avise o usuário antes de prosseguir, já que um push nesse estado não segue o fluxo normal de branch.
- **Nada para commitar**: informe que a árvore de trabalho está limpa e não crie um commit vazio.
- **Conflitos de merge não resolvidos**: não commite; peça para o usuário resolver os conflitos primeiro.