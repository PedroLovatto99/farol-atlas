# Deploy do Farol Atlas

Guia para colocar o Farol Atlas no ar: **API, worker, banco e proxy reverso numa VM ARM (Ampere) da
Oracle**, com Docker Compose e Caddy, e **o frontend na Vercel**. O repositório não faz deploy
sozinho: tudo abaixo é feito por você, uma vez, e depois repetido a cada atualização.

```
navegador ──► Vercel (frontend, arquivos estáticos)
    │
    └──► https://<sub>.duckdns.org ──► Caddy (80/443) ──► api (8000, só rede interna) ──► postgres
                                                              ▲
                                                           worker (coletas)
```

- Só o **Caddy** publica portas (80 e 443). A API e o banco ficam em redes internas do Docker.
- O Caddy emite e renova o certificado (Let's Encrypt) sozinho. Os certificados ficam no volume
  `caddy-dados`: não se perdem ao atualizar nem ao recriar os contêineres.
- Arquivos desta parte do projeto: `docker-compose.prod.yml`, `deploy/Caddyfile`,
  `ferramentas/backup-banco.sh`, `ferramentas/verificar-caddy.sh`, `frontend/vercel.json`.

## 1. O que você precisa antes

- Uma VM **VM.Standard.A1.Flex** (Ampere, arm64) da Oracle com Ubuntu 22.04 ou 24.04. Reserve um
  **IP público fixo** (Networking → Reserved public IPs): se o IP mudar, o DuckDNS aponta para o
  lugar errado.
- Uma conta no [DuckDNS](https://www.duckdns.org) com um subdomínio (ex.: `farol-api`).
- Uma conta na [Vercel](https://vercel.com) ligada ao repositório do GitHub.
- A chave do Gemini (`GOOGLE_API_KEY`) e um contato para o User-Agent da coleta (`CONTATO_COLETA`).

Confira na VM que ela é ARM: `uname -m` deve mostrar `aarch64`.

## 2. Preparar a VM

### 2.1 Docker no Ubuntu ARM

```bash
sudo apt-get update && sudo apt-get -y upgrade
sudo apt-get -y install ca-certificates curl git gnupg iptables-persistent
# (o iptables-persistent pergunta se quer salvar as regras atuais: responda Sim)

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"     # saia e entre de novo na VM para valer
docker run --rm hello-world         # deve funcionar sem sudo
```

O `dpkg --print-architecture` devolve `arm64` sozinho. As imagens usadas (`caddy:2`, `postgres:18` e
`python:3.13-slim`) têm versão `linux/arm64`, e as dependências Python do backend têm wheel para
`aarch64` (o CI confere as duas coisas).

### 2.2 Liberar as portas 80 e 443

São **duas** camadas e as duas precisam estar abertas.

**a) Security list da Oracle** (console da Oracle Cloud): Networking → Virtual cloud networks → sua
VCN → Security Lists → a lista da sub-rede da VM → *Add Ingress Rules*, duas regras:

| Source CIDR | Protocolo | Porta de destino |
| ----------- | --------- | ---------------- |
| `0.0.0.0/0` | TCP       | `80`             |
| `0.0.0.0/0` | TCP       | `443`            |

(Se a VM usa um *Network Security Group*, a regra vai nele.) Não abra a 5432 nem a 8000: elas não
são publicadas e não devem ser.

**b) iptables da própria VM.** As imagens Ubuntu da Oracle vêm com regras que terminam num `REJECT`;
as portas precisam entrar **antes** dele, e depois as regras têm de ser salvas para sobreviver a
reinício.

```bash
sudo iptables -L INPUT -n --line-numbers      # veja em que linha está o REJECT (costuma ser a 6)
sudo iptables -I INPUT 6 -p tcp -m state --state NEW --dport 80  -j ACCEPT
sudo iptables -I INPUT 6 -p tcp -m state --state NEW --dport 443 -j ACCEPT
sudo netfilter-persistent save                # grava em /etc/iptables/rules.v4 (persistente)
sudo iptables -L INPUT -n --line-numbers      # confira: 80 e 443 acima do REJECT
```

Use o número da linha do `REJECT` no lugar do `6`, se for outro. Não use `ufw` junto com isso. Teste
de fora da VM, depois de subir tudo (passo 5): `curl -I https://SEU-SUBDOMINIO.duckdns.org/api/v1/saude`.

## 3. DuckDNS

1. No painel do DuckDNS, crie o subdomínio e aponte-o para o **IP público fixo** da VM.
2. O domínio completo (ex.: `farol-api.duckdns.org`) será o `DOMINIO` do `.env`.
3. Se você não reservou o IP, o endereço pode mudar; nesse caso, atualize-o por cron. O token fica
   num arquivo só seu, fora do repositório:

   ```bash
   mkdir -p ~/.duckdns && chmod 700 ~/.duckdns
   echo 'TOKEN-DO-DUCKDNS' > ~/.duckdns/token && chmod 600 ~/.duckdns/token
   ( crontab -l 2>/dev/null; echo '*/5 * * * * curl -fsS "https://www.duckdns.org/update?domains=farol-api&token=$(cat $HOME/.duckdns/token)&ip=" >/dev/null' ) | crontab -
   ```

O Caddy só consegue o certificado se o nome já apontar para a VM **e** as portas 80/443 estiverem
abertas. Confira antes de subir: `dig +short farol-api.duckdns.org`.

## 4. Clonar e criar o `.env` de produção

```bash
git clone https://github.com/PedroLovatto99/FarolAtlas.git ~/FarolAtlas
cd ~/FarolAtlas
git checkout main            # ou a tag/branch que você vai publicar
cp .env.example .env
chmod 600 .env
nano .env
```

O `.env` **só existe no servidor** (`.gitignore` já o ignora). Variáveis de produção:

| Variável | Valor |
| -------- | ----- |
| `DOMINIO` | o subdomínio completo, ex.: `farol-api.duckdns.org` |
| `POSTGRES_PASSWORD` | uma senha forte **só com letras e números**: `openssl rand -hex 24` |
| `POSTGRES_USER` / `POSTGRES_DB` | opcionais (padrão `farol`) |
| `CORS_ORIGENS` | o endereço da Vercel, só `https://`, ex.: `https://farol-atlas.vercel.app` (vários, separados por vírgula) |
| `COLETAS_AUTOMATICAS` | `true` em produção. **Obrigatória:** sem ela a API e o worker se recusam a subir |
| `CONTATO_COLETA` | URL ou e-mail que vai no User-Agent da coleta (não deixe o valor de exemplo) |
| `GOOGLE_API_KEY` | a chave do Gemini |
| `LLM_CLASSIFICADOR` / `LLM_TRADUTOR` | opcionais (padrão `google_genai:gemini-3.6-flash`) |
| `LIMITE_PEDIDOS_POR_MINUTO` / `LIMITE_RAJADA` | opcionais (padrão 120 e 40) |

Não coloque `DATABASE_URL` nem `AMBIENTE` no `.env`: o compose de produção monta a URL do banco com
`POSTGRES_PASSWORD` e define `AMBIENTE=producao` e `PROXY_CONFIAVEL`. Remova também do `.env` as
linhas de desenvolvimento que sobraram do exemplo (`DATABASE_URL_TESTE`, `API_DOCS_HABILITADA=true`,
`VITE_API_URL`, `OLLAMA_BASE_URL`).

Em produção a partida **falha de propósito** se `CORS_ORIGENS` não tiver só origens `https://`, se
faltar a rede do proxy (já definida no compose) ou se `COLETAS_AUTOMATICAS` não estiver definida.

## 5. Subir

```bash
cd ~/FarolAtlas
docker compose -f docker-compose.prod.yml config --quiet      # confere o .env
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps                  # api, caddy, postgres, worker "healthy"
curl -fsS https://farol-api.duckdns.org/api/v1/saude          # {"banco":"ok",...}
```

A primeira subida compila a imagem (alguns minutos na Ampere), aplica as migrações e o seed
(`migracao` roda uma vez e termina) e o Caddy pede o certificado. Se o `curl` der erro de
certificado, veja `docker compose -f docker-compose.prod.yml logs caddy`: quase sempre é DNS ainda
não propagado ou porta fechada (passo 2.2).

Com `COLETAS_AUTOMATICAS=true` o worker coleta sozinho na partida (se não houver coleta recente) e
nos horários agendados. Para forçar uma coleta agora:

```bash
docker compose -f docker-compose.prod.yml exec worker python -m farol.worker coletar --alertas
docker compose -f docker-compose.prod.yml exec worker python -m farol.worker coletar --postos
docker compose -f docker-compose.prod.yml exec worker python -m farol.worker coletar --vistos
```

Os comandos do dono para os vistos (`vistos pendentes`, `vistos confirmar ...`) funcionam do mesmo
jeito, com `exec worker python -m farol.worker vistos ...`.

### Como a API se comporta atrás do Caddy

- **IP do visitante.** O Caddy escreve o `X-Forwarded-For` com o endereço que ele viu e descarta o
  que o visitante mandar. A API só confia nesse cabeçalho quando o pedido vem da rede interna
  `172.30.0.0/24` (a rede `publica` do compose, onde só o Caddy chama a API). Quem falar com a API
  de outro lugar não consegue forjar o IP.
- **Limite de pedidos.** 120 por minuto por IP, com rajada de 40, e `429` com `Retry-After`. O
  `/api/v1/saude` fica de fora. O valor é folgado de propósito: operadoras móveis brasileiras põem
  muitos clientes atrás do mesmo IP (CGNAT). O contador fica na memória do processo, por isso o
  compose fixa **`--workers 1`**: com N processos, o limite efetivo seria de até N vezes o
  configurado. Mude só se souber o que está fazendo (e então divida o limite por N).
- **Cache.** `/mapa`, `/paises/{codigo}` e `/vistos` ficam 5 minutos na memória, mas qualquer
  escrita (coleta, classificação, comando do dono) sobe um contador no banco e invalida tudo: depois
  de uma coleta nova, ninguém recebe dado antigo por mais de **15 segundos**. O navegador recebe
  `Cache-Control: public, max-age=60`. Se o banco estiver fora do ar, o cache é ignorado.

## 6. Vercel (frontend)

1. *Add New → Project* e importe o repositório.
2. **Root Directory:** `frontend`. O `frontend/vercel.json` já define o resto (Vite, `npm ci`,
   `npm run build`, saída `dist`, regra de SPA que manda qualquer rota para `index.html` e os
   cabeçalhos de segurança); confira que o painel mostra esses valores.
3. *Environment Variables:* **`VITE_API_URL`** = `https://farol-api.duckdns.org` (sem barra no fim;
   o prefixo `/api/v1` o frontend acrescenta). Marque *Production*. A variável é lida **na hora do
   build**: se mudar, faça um novo deploy.
4. Faça o deploy e copie o endereço de produção (ex.: `https://farol-atlas.vercel.app`).
5. Volte ao servidor, ponha esse endereço em `CORS_ORIGENS` no `.env` e reaplique:

   ```bash
   docker compose -f docker-compose.prod.yml up -d api
   ```

O navegador chama a API direto (CORS): a API aceita **só** as origens listadas, só `GET` e sem
credenciais. Deploys de pré-visualização da Vercel (`*.vercel.app` com outro endereço) não ficam
liberados; se precisar de um, acrescente o endereço dele a `CORS_ORIGENS` (curingas não são aceitos).

## 7. Backup

`ferramentas/backup-banco.sh` faz `pg_dump` pelo compose de produção, compacta em
`backups/farol-AAAAMMDD-HHMMSS.sql.gz` e guarda só as últimas **14** cópias (`COPIAS_A_MANTER`
muda; `DESTINO_BACKUP` muda a pasta). Se o dump falhar ou vier vazio, o script sai com erro e **não
apaga** as cópias antigas.

```bash
chmod +x ferramentas/backup-banco.sh
ferramentas/backup-banco.sh        # teste uma vez à mão
```

Agende no cron do seu usuário (`crontab -e`), por exemplo todo dia às 03:30:

```cron
30 3 * * * cd $HOME/FarolAtlas && ferramentas/backup-banco.sh >> $HOME/backup-farol.log 2>&1
```

As cópias ficam na própria VM. Se a VM se perder, elas se perdem junto: copie a pasta `backups/`
de vez em quando para outro lugar (`scp`, bucket gratuito do Oracle Object Storage etc.).

### Restaurar um backup

Substitui o banco inteiro pelo conteúdo da cópia. Os dados atuais são apagados.

```bash
cd ~/FarolAtlas
F=docker-compose.prod.yml
COPIA=backups/farol-20261030-033000.sql.gz       # escolha a cópia: ls -lt backups/

docker compose -f $F stop api worker             # ninguém grava durante a restauração

# recria o banco vazio (conectando no banco "postgres", não no do Farol)
docker compose -f $F exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
     -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\" WITH (FORCE)" \
     -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\""'

# carrega a cópia numa transação só (se algo falhar, nada é aplicado)
gunzip -c "$COPIA" | docker compose -f $F exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 --single-transaction -q' >/dev/null

docker compose -f $F up -d                       # a migração confere o esquema e sobe tudo
curl -fsS https://farol-api.duckdns.org/api/v1/saude
```

Quando a restauração acaba, o contador de versão dos dados volta ao valor da cópia; o cache da API
é refeito no máximo em 15 segundos e, se quiser na hora, `docker compose -f $F restart api`.

## 8. Atualizar e voltar uma versão

### Atualizar

```bash
cd ~/FarolAtlas
ferramentas/backup-banco.sh                          # sempre antes
git tag "antes-$(date +%Y%m%d-%H%M)"                 # marca de onde você está
docker tag farol-backend farol-backend:anterior      # guarda a imagem em uso
git fetch --all --tags && git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl -fsS https://farol-api.duckdns.org/api/v1/saude
```

A `migracao` roda a cada `up` (`alembic upgrade head`, mais o seed, que é idempotente). O volume do
banco e o dos certificados do Caddy **não** são tocados pelo `up`. Nunca use `down -v`: ele apaga
os volumes (banco e certificados).

### Voltar uma versão

Sem mudança de esquema no banco entre as duas versões (o caso comum), basta voltar a imagem:

```bash
cd ~/FarolAtlas
docker tag farol-backend:anterior farol-backend
git checkout antes-20261030-1200                     # a marca criada ao atualizar
docker compose -f docker-compose.prod.yml up -d --no-build
```

Se a versão nova trouxe uma migração e a antiga não a conhece, **restaure também o backup** feito
antes da atualização (seção 7) com o código antigo no lugar. Migrações novas deste repositório só
acrescentam (a `0004`, por exemplo, só cria a tabela `versao_dados`), mas confira o arquivo em
`backend/alembic/versions/` antes de decidir.

Depois de voltar, para publicar de novo a versão mais nova: `git checkout main && git pull` e
`up -d --build`.

## 9. No dia a dia

```bash
F="-f docker-compose.prod.yml"
docker compose $F ps                              # estado e healthchecks
docker compose $F logs -f --tail 100 api          # log da API
docker compose $F logs --tail 200 worker          # log do worker (também em arquivo, abaixo)
docker compose $F exec worker tail -n 100 /app/logs/worker.log
docker compose $F restart worker
```

- **Logs do Docker:** rodam em rotação (10 MB × 5 arquivos por serviço).
- **Log do worker:** além da saída do Docker, o worker grava `/app/logs/worker.log` (5 MB × 5
  cópias) num volume nomeado (`logs-worker`). Ele **sobrevive** a `up -d --build`, a
  `--force-recreate` e a `docker compose rm`; só `down -v` o apaga.
- **Desligar as coletas automáticas:** ponha `COLETAS_AUTOMATICAS=false` no `.env` e rode
  `docker compose $F up -d worker`. O worker continua de pé, sem agendar nada, e os comandos
  `coletar ...` seguem funcionando à mão. Em produção a variável é obrigatória (`true` ou `false`).
- **Disco:** `docker system df` mostra o espaço usado por imagens e volumes;
  `docker image prune` apaga imagens antigas que sobram dos `--build`.

## 10. Em desenvolvimento nada muda

O `docker-compose.yml` (desenvolvimento) segue igual: `docker compose up --build`, CORS pelo
`.env`, API com `--reload`. Fora de produção, `COLETAS_AUTOMATICAS` indefinida significa
**desligada** (o `.env.example` já traz `false`): o worker de desenvolvimento não coleta sozinho.
Para coletar à mão: `docker compose exec worker python -m farol.worker coletar --alertas`.
O limite de pedidos (120/40 por minuto) e o cache também valem em desenvolvimento; para desligá-los
use `LIMITE_PEDIDOS_POR_MINUTO=0` e `CACHE_TTL_SEGUNDOS=0` no `.env`.

## Teste de fumaça do compose de produção (no PC, sem coletar nada)

Antes do primeiro deploy, o `docker-compose.prod.yml` foi subido inteiro no Docker Desktop do
desenvolvedor, com o nome de projeto `farol-prod-teste` (`-p`), que não toca nos volumes de
desenvolvimento, e um `.env` de teste: `DOMINIO=localhost`, `AMBIENTE=producao`,
`COLETAS_AUTOMATICAS=false` (nenhuma coleta real), `CORS_ORIGENS=https://localhost` e uma senha de
banco aleatória. Resultado de 30/10/2026:

| Checagem | Resultado |
| -------- | --------- |
| Contêineres | `api`, `caddy`, `postgres` e `worker` saudáveis (healthy); `migracao` terminou com código 0 |
| `https://localhost/api/v1/saude` e `/api/v1/mapa` pelo Caddy (certificado local, `curl -k`) | 200 nos dois; `/mapa` com 90 KB, `Cache-Control: public, max-age=60`; `/saude` com `no-store` |
| Cabeçalhos de segurança | HSTS sem preload, `nosniff`, `Referrer-Policy`, CSP `default-src 'none'; frame-ancestors 'none'` |
| CORS | `Access-Control-Allow-Origin: https://localhost` para a origem permitida; nada para `https://malicioso.exemplo`; preflight de POST recusado (400) |
| Rajada | 80 pedidos seguidos a `/mapa`: o primeiro 429 veio no 51º (40 de rajada mais o que o balde repôs durante o teste); o 429 traz `Retry-After` e o cabeçalho do CORS; `/saude` seguiu respondendo 200 |
| `X-Forwarded-For` forjado | pelo Caddy: um IP diferente forjado a cada pedido não evitou o 429, porque o Caddy o substitui. Direto à API, a partir de outro contêiner (que não é o Caddy): 60 pedidos com IPs forjados diferentes deram 40 × 200 e 20 × 429 (um balde só) |
| Worker | de pé; log "coletas automáticas DESLIGADAS"; agendador iniciado sem nenhum job; zero execuções de coleta e zero alertas no banco; o `worker.log` ficou no volume e continuou entre duas partidas |
| Portas | só o caddy publica portas (`0.0.0.0:80` e `0.0.0.0:443`); `api`, `worker` e `postgres` não publicam nenhuma |
| Logs e reinício | os quatro serviços em `json-file` com `max-size 10m` e `max-file 5`, `restart: unless-stopped` |
| Limpeza | `down -v` só em `-p farol-prod-teste`; nenhum contêiner, rede ou volume do projeto de teste sobrou, e o volume de desenvolvimento ficou intacto |

O teste achou um defeito que os testes automáticos não pegavam: a API sobe antes do Caddy e o
Docker lhe dava o `172.30.0.2`, o endereço fixo reservado ao Caddy, que então não subia
("Address already in use"). A rede `publica` agora tem `ip_range: 172.30.0.128/25`, de modo que os
endereços dinâmicos nunca colidem com o do Caddy (há um teste para isso).

Para repetir o teste sem mexer no seu `.env` real (o compose lê sempre o `.env` ao lado dele),
copie `backend/`, `dados/`, `deploy/` e `docker-compose.prod.yml` para uma pasta à parte, crie lá o
`.env` de teste e rode `docker compose -p farol-prod-teste -f docker-compose.prod.yml up -d --build`.
Se também tiver o ambiente de desenvolvimento, troque lá o nome da imagem (`image: farol-backend`)
para não sobrescrever a imagem de desenvolvimento. As portas 80 e 443 do PC precisam estar livres.
Para acabar: `docker compose -p farol-prod-teste -f docker-compose.prod.yml down -v`, sempre com o
`-p`.

## Checagens automáticas (CI)

O CI valida, a cada pull request: o `Caddyfile` (`caddy validate`); o `docker-compose.prod.yml`
(`config`); que as imagens têm `linux/arm64`; o Caddy de verdade na frente de uma API de mentira
(`ferramentas/verificar-caddy.sh`: X-Forwarded-For forjado não passa, cabeçalhos de segurança,
corpo máximo de 1 KB e compressão); e, nos testes do backend, o script de backup, as regras do
compose (só o Caddy publica portas, o banco não publica nenhuma, volumes, `restart`, healthchecks,
rotação de logs) e que toda dependência Python de produção tem wheel para `aarch64`.
