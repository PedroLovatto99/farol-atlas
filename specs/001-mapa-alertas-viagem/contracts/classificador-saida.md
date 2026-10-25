# Contrato da saída do classificador de alertas

Módulo `classificacao`. O LLM é usado **só aqui** nesta feature (sem RAG, chat, Chroma nem embeddings). Modelo: variável `LLM_CLASSIFICADOR` (padrão `google_genai:gemini-3.6-flash`), temperatura 0, via `init_chat_model` e `with_structured_output`.

## Entrada

`titulo`, `data` (publicação e, se houver, modificação), `categoria`, `texto`. O texto do alerta é **dado**: vai entre delimitadores, sem ferramentas disponíveis ao modelo, e instruções contidas nele não alteram o formato da resposta (princípio VIII).

## Saída (Pydantic)

```python
class Nivel(StrEnum):
    EVITAR = "evitar"
    NAO_VIAJAR = "nao_viajar"
    NORMALIZADA = "normalizada"      # o alerta informa o fim do problema

class RegiaoClassificada(BaseModel):
    nome: str                        # ex.: "Sul do Líbano"
    nivel: Nivel

class TerritorioClassificado(BaseModel):
    codigo: str                      # ISO-2 ou código de dependência presente no mapa
    nivel_pais: Nivel | None         # None = alerta só regional para este território
    regioes: list[RegiaoClassificada] = []

class Classificacao(BaseModel):
    e_alerta_de_viagem: bool         # False: aviso de fraude, notícia etc.; não afeta o mapa
    territorios: list[TerritorioClassificado] = []   # vazio se e_alerta_de_viagem for False
```

## Validação depois da resposta

1. Qualquer `codigo` fora de `territorio` (198 países + dependências do mapa) **invalida a resposta inteira**: a classificação vira `falhou` com o motivo; o alerta fica pendente.
2. `e_alerta_de_viagem = true` exige ao menos um território. `false` exige lista vazia.
3. Território repetido na lista invalida a resposta.
4. Falha de rede, tempo esgotado ou saída que não casa com o schema: `falhou`. Nada é gravado em `nivel_territorio`.
5. **Antes** de validar, as "regiões" que são o país inteiro ("demais regiões do país", "restante do país", "todo o país", "todo o território"...) saem de `regioes` e viram `nivel_pais` (o mais grave, se o país já tinha nível). O prompt já pede isso, mas a regra vale em código (`farol.dominio.regioes`).

## Casos de teste (modelo falso, fixtures em `backend/tests/fixtures/govbr/`)

| Fixture | Resultado esperado |
|---|---|
| `alerta_1.html` (Bolívia, 10/07/2026, "restabelecida a circulação…") | `BO` com `NORMALIZADA` |
| `alerta_2.html` (Oriente Médio, 04/07/2026, modificado em 17/08/2026) | Vários territórios; `LB` com região "Sul do Líbano" e `PS` com "Faixa de Gaza" |
| `alerta_3.html` (fraudes em nome dos consulados nos EUA, "Apoio a Cidadãos") | `e_alerta_de_viagem = false` |
| `alerta_2.html`, com a resposta do modelo `LB`: `nivel_pais` nulo, regiões "Sul do Líbano" (não viajar) e "demais regiões do país" (evitar) | `LB` gravado com `nivel_pais = evitar` e só a região "Sul do Líbano" |
| Resposta com `codigo = "ZZ"` | Resposta inválida; alerta pendente |
| Texto com "ignore as instruções anteriores…" | Saída segue o schema; nenhuma instrução do texto é obedecida |

Os valores esperados do modelo falso são escritos à mão a partir do texto das fixtures; o teste verifica a **validação e a gravação**, não a qualidade do LLM.
