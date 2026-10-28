# Contrato: meios restritos ao dono

O padrão da 001 é `python -m farol.worker <comando>`, que em produção roda **dentro do contêiner do worker** (`docker compose exec worker …`). Não há rota HTTP, tela nem autenticação para isso: quem tem acesso ao contêiner é o dono. Nenhum destes comandos aparece na API pública (princípio VIII).

## Comandos

| Comando | O que faz |
|---|---|
| `python -m farol.worker coletar --vistos` | Uma rodada de coleta de vistos agora (ignora o calendário, mas respeita o `robots.txt`, a pausa e a regra de estabilidade). Imprime o resumo. |
| `python -m farol.worker vistos pendentes` | Lista tudo o que espera o dono: mudanças retidas, nomes e rótulos pendentes, e regras por país a reconfirmar (com o hash novo para colar no arquivo). |
| `python -m farol.worker vistos confirmar <codigo>` ou `--todos` | Aplica a(s) mudança(s) retida(s): o candidato vira o dado exibido, com a data da coleta que o leu. |
| `python -m farol.worker vistos rejeitar <codigo>` | Rejeita a mudança retida. Vale enquanto a fonte mantiver o mesmo valor lido; se a fonte mudar de novo, a decisão recomeça. |
| `python -m farol.worker vistos ignorar-nome "<nome>" --motivo "<texto>"` | Marca um **nome** pendente como ignorado de propósito, com motivo (obrigatório). Rótulos não podem ser ignorados. |

Exemplo em desenvolvimento:

```powershell
docker compose exec worker python -m farol.worker coletar --vistos
docker compose exec worker python -m farol.worker vistos pendentes
docker compose exec worker python -m farol.worker vistos confirmar AR
```

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | Feito. Em `coletar`: coleta **válida**. |
| 1 | `coletar`: a coleta não foi válida (`rejeitada`, `adiada`, `falhou` ou `bloqueada`); o motivo está no resumo. |
| 2 | Uso errado ou configuração: `CONTATO_COLETA` ausente ou de exemplo; código sem mudança retida; nome que não está pendente; motivo ausente. |

## Resumo de `coletar --vistos`

```text
Coleta de vistos VÁLIDA: 228 países reconhecidos (mínimo 206)
Artigo: revisão 1380975986, última edição em 19/10/2026 05:08 UTC
Dados aplicados: 3 | sem mudança: 222 | retidos: 1
Retidos (esperam confirmação; veja `vistos pendentes`):
  AR  Visto exigido → Isento de visto
Nomes não reconhecidos: 0 | rótulos não reconhecidos: 0
Traduções: 4 novas (1 lote), 0 falhas
```

(O exemplo acima é só de forma; as linhas reais saem da implementação.) Em coleta não válida:

```text
Coleta de vistos ADIADA: a última edição do artigo foi há 6 h (mínimo 24 h). Tentativa 1 de 3; nova tentativa amanhã.
```

## `vistos pendentes`

```text
Mudanças retidas (1)
  código  exibido → lido                 desde       dado exibido de
  AR      Visto exigido → Isento de visto  27/10/2026  20/10/2026
Nomes não reconhecidos (0)
Rótulos não reconhecidos (0)
Regras por país a reconfirmar (1)
  JM  a nota mudou; hash esperado 3f1a…, hash novo 9c07…; texto novo: "…"
```

## Registro operacional (log do worker)

Uma linha JSON por evento (o formato da 001), com os números em `dados`:

| Quando | Nível | Mensagem | `dados` |
|---|---|---|---|
| Rodada **agendada** termina com algum pendente | `WARNING` | `vistos: há pendências para o dono` | `retidas`, `nomes_pendentes`, `rotulos_pendentes`, `regras_pendentes` |
| Retidas passam de 10% dos países reconhecidos | `WARNING` | `vistos: possível vandalismo em massa na fonte` | `retidas`, `reconhecidos`, `percentual` |
| Rodada adiada ou falha técnica | `INFO` / `WARNING` | `vistos: rodada adiada` / `vistos: rodada falhou` | `motivo`, `tentativa`, `proxima_tentativa` |
| Bloqueio | `WARNING` | `vistos: coleta interrompida` | `motivo` |
| Formato inesperado (coleta `rejeitada`) | `WARNING` | `vistos: coleta rejeitada por formato inesperado: o leitor da página precisa de manutenção (mudança de estrutura na fonte)` | `motivo` |
| País com mudança retida (inclusive a saída da linha) | `WARNING` | `vistos: mudança retida` | `codigo`, `exibida`, `lida` (`sem_informacao` quando nula) |

## Agenda

| Job | Quando (America/Sao_Paulo) | Observação |
|---|---|---|
| `vistos-semanais` | segunda-feira, 05:13 (decisão O5) | `coalesce`, `max_instances=1`, mesma tolerância de atraso dos alertas |
| `vistos-na-partida` | ao subir o worker, se a última tentativa tem mais de 7 dias | como `postos-na-partida` |
| `vistos-amanha` | 05:13 do dia seguinte a uma rodada `adiada` ou `falhou` | até 3 seguidas; depois só a próxima segunda (O6) |
