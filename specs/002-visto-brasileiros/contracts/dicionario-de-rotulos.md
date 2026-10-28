# Contrato: dicionários de rótulos, nomes e regras por país

> **Status: formato e regras APROVADOS em 28/10/2026** (levantamento do `research.md`, seção 3, e decisões O1 a O4). Este documento fixa o **formato**, as regras de leitura e os testes. O **conteúdo** dos três arquivos (as entradas) é escrito na implementação, a partir de `research.md` 3.1 a 3.5, e cada entrada leva um teste.

Local: `backend/src/farol/vistos/dicionarios_yaml/` (dentro do pacote, para ir na imagem do Docker e ser testado com o código). Arquivos YAML em UTF-8, lidos uma vez por execução e validados ao carregar (erro de formato derruba o teste, não a coleta em produção).

## Normalização (antes de qualquer consulta)

Aplicada ao texto da fonte e às chaves dos arquivos, pelas mesmas funções (`vistos/normalizacao.py`), com testes próprios. Valem para **todo** texto (rótulos, nomes, prazos e observações):

1. remove marcas de referência (`[2]`, `[ 374 ]`, `<sup>`);
2. troca espaços não separáveis por espaço comum e colapsa espaços repetidos;
3. uniformiza aspas e apóstrofos tipográficos (`’` → `'`);
4. para **chave de consulta**: caixa baixa (`casefold`). O texto exibido mantém a caixa da fonte.

Vale **só para os rótulos** de situação (`normalizar_rotulo` e `chave_de_rotulo`):

5. uniformiza a barra: `A/B`, `A /B` e `A/ B` viram `A / B`. É o separador das partes de um rótulo combinado, por isso só aqui.

Observações, nomes e prazos **não** têm a barra mexida: ficam como na fonte, só com a limpeza dos itens 1 a 3 (ex.: "15/30 pounds sterling" continua assim).

## `rotulos.yaml`: rótulos atômicos

**Regra geral de categoria (O1; vale para qualquer rótulo, atual ou futuro).** A categoria reflete **o que é preciso fazer antes de embarcar**:

- "online" e "e-" descrevem só o **canal** do pedido, nunca a categoria por si;
- **processo de visto completo** é `visto_exigido`, mesmo quando feito online (ex.: `online visa required`, Austrália);
- **pedido online simplificado** (autorização, e-visa rápido, e-VOA) é `autorizacao_eletronica` (ex.: `evisa`, `e-voa`, `eta`, `electronic travel authorization`);
- algo obtido **na chegada** é `visto_na_chegada` (ex.: `visa on arrival`, `entry permit on arrival`);
- rótulo que não caiba na regra é cadastrado como `outra_situacao` até o dono decidir.

Cada entrada traz um campo `motivo` (uma frase) que cita a regra aplicada, para o próximo leitor do arquivo. A parte `online visa` (sem "required") só existe dentro do combinado `Online Visa / Visa on arrival` (Burundi, Nepal) e está cadastrada como `autorizacao_eletronica` (`research.md` 3.1); o dono pode mudá-la.

Chave: rótulo normalizado, em minúsculas. Cada entrada:

```yaml
visa not required:
  categoria: isento              # isento | visto_na_chegada | autorizacao_eletronica | visto_exigido | outra_situacao
  exemplo: Albania               # um país da fixture que tem este rótulo (documentação e teste)
freedom of movement:
  categoria: isento
  aceita_rg: true                # só vale se a nota tiver "ID card" (research.md 3.2)
online visa required:
  categoria: visto_exigido
  motivo: visto completo pedido online (o canal não muda a categoria)
e-voa:
  categoria: autorizacao_eletronica
  motivo: pedido online simplificado
permit required:
  categoria: outra_situacao      # rótulo CONHECIDO mapeado de propósito para "Outra situação"
  exemplo: Tokelau
```

Regras de leitura de um rótulo `R` da fonte:

1. `R` normalizado está no dicionário ⇒ usa a entrada.
2. Senão, separa `R` em " / ". Se houver mais de uma parte e **todas** estiverem no dicionário ⇒ combinado: vale a categoria **mais exigente** das partes (isento < visto na chegada < autorização ou visto eletrônico < visto exigido); **qualquer parte** em `outra_situacao` ⇒ o resultado é `outra_situacao` com motivo `rotulo_conhecido`.
3. Qualquer parte fora do dicionário ⇒ `outra_situacao` com motivo `rotulo_desconhecido`, e o rótulo inteiro vai para `item_para_revisao` (tipo `rotulo`). O país **não** é descartado: aparece em "Outra situação" com o rótulo original visível.
4. `aceita_rg` do resultado é verdadeiro só se a entrada tiver `aceita_rg: true` **e** a nota da linha contiver `ID card`; caso contrário falso (e, se faltar a frase, uma linha de aviso no log).

Cada entrada tem um teste (`tests/unidade/vistos/test_dicionario_rotulos.py`, parametrizado pelo arquivo): chave normalizada, categoria esperada. Os combinados da fixture têm testes de ponta a ponta (`test_rotulos_combinados.py`).

## `nomes.yaml`: nomes da fonte → código do mapa

```yaml
nomes:
  Albania: AL
  Brunei: BN
  United Kingdom and Crown dependencies: GB
  Macau: MO
  Saint Helena: SH
  Ascension Island: SH
  Tristan da Cunha: SH
ignorar:
  Kosovo: Usa a identidade da Sérvia, por convenção da 001
  Abkhazia: Território não reconhecido, sem desenho no mapa
```

- A chave é o nome normalizado, sem diferenciar maiúsculas. Contém **todos** os nomes da fonte que se ligam a um código (o `pycountry` não vai para produção) e os ignorados de propósito, cada um com motivo.
- Cada código tem de existir em `territorio` (o teste confere contra o seed) e **não pode** ser de área neutra. Um nome não pode estar nas duas listas.
- Nome fora das duas listas ⇒ `item_para_revisao` (tipo `nome`); a linha não afeta nenhum território.
- Várias linhas da fonte para o mesmo código (Santa Helena, Ascensão e Tristão da Cunha; a linha do Reino Unido e das dependências da Coroa) ⇒ tratadas como partes de um rótulo combinado (FR-007).
- As convenções de território da 001 **não** são repetidas aqui: o painel de Kosovo e de Malvinas já é o do soberano pelo cadastro (`identidade_do_soberano`), e o `ignorar` apenas evita ler a linha própria deles.

## `regras_por_pais.yaml`: "varia conforme o motivo da viagem"

```yaml
JM:
  varia_conforme_motivo: true        # nota "90 days (business), 6 months (tourist)"
  prazos_diferem_por_motivo: true    # o campo de permanência mostra "Varia conforme o motivo"
  hash_observacao: "<sha256>"        # da observação em que a regra se baseou
ZM:
  varia_conforme_motivo: true
  prazos_diferem_por_motivo: true
  hash_observacao: "<sha256>"
```

Lista curada, sem heurística de texto (`research.md` 3.5). Hoje só `JM` e `ZM`; o México, Angola e o Líbano ficam de fora de propósito.

**`hash_observacao`:** SHA-256 (UTF-8, hexadecimal) das **notas normalizadas** (função de normalização acima, sem a barra, que só vale nos rótulos) das linhas da fonte daquele código, na ordem da fonte, unidas por quebra de linha. A cada coleta válida, o serviço recalcula o hash de cada código da lista:

- igual ao guardado ⇒ nada a fazer (e fecha o item de revisão aberto, se houver);
- diferente ⇒ o país entra na **lista de revisão** (`item_para_revisao`, tipo `regra`, valor = código), com o texto novo e o hash novo no contexto, e `vistos pendentes` o mostra. A regra continua valendo enquanto isso (o efeito é só uma nota informativa), e a pendência **não** invalida a coleta;
- o dono reconfirma colando o hash novo no arquivo (ou removendo o país); na coleta seguinte o hash bate e o item se resolve sozinho. Regra pendente não pode ser ignorada.

## Testes obrigatórios do dicionário (sobre a fixture)

| Teste | O que garante |
|---|---|
| Todo rótulo distinto da fixture é reconhecido | SC-010: nenhum rótulo desconhecido na tabela atual |
| Todo nome da fixture está em `nomes` ou `ignorar` | SC-009 e o registro vazio depois da primeira coleta |
| Cada entrada de `rotulos.yaml` | categoria esperada, uma por uma |
| Cada combinado da fixture | categoria mais exigente; "Outra situação" combinada vence |
| `aceita_rg` | 8 de 8 do rótulo `Freedom of Movement` (AR, BO, CL, CO, EC, PY, PE, UY); Guiana e Venezuela de fora |
| Regra geral de categoria | Austrália `visto_exigido`; Indonésia e Libéria `autorizacao_eletronica`; Samoa e Ilhas Salomão `visto_na_chegada`; Burundi e Nepal `autorizacao_eletronica` |
| Regras por país | o hash da fixture bate com `JM` e `ZM`; nota alterada abre o item de revisão; hash igual o fecha; México, Angola e Líbano não estão na lista |
| Códigos | todos existem no seed; nenhum é neutro |
| Cobertura | 100% dos territórios com painel têm linha própria ou do soberano |
