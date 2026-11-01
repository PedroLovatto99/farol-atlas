# Specification Quality Checklist: Chat de dúvidas de viagem com base nos alertas e nos dados do site

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-31
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (6 permanecem, de propósito; ver Notes)
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Marcadores [NEEDS CLARIFICATION] (6)**: os seis pontos deixados em aberto na especificação inicial foram resolvidos em `/speckit-clarify` na sessão de 01/11/2026 (cinco perguntas; contexto da conversa e tempo máximo foram agrupados). Nenhum marcador permanece:
  1. **FR-026, FR-026a, FR-026b**: 20 perguntas por hora por IP e teto global de 500 por dia (horário de Brasília); falhas por indisponibilidade não contam.
  2. **FR-020**: contexto de 6 mensagens (3 pares), usado só para entender a pergunta e sempre tratado como não confiável.
  3. **FR-027**: resposta em até 20 s, com indicação do que o chat está fazendo; passado o tempo, avisa e oferece tentar de novo.
  4. **FR-008**: alerta novo, alterado, removido ou substituído vale (ou deixa de valer) no chat em até 15 minutos depois da coleta completa que confirmou a mudança.
  5. **FR-005a**: título, data e link, mais um bloco "Ver trecho" recolhido, com o texto original do alerta, nunca reescrito.
  6. **FR-033**: 60 perguntas-gabarito, ao menos 5 por tipo, e recuperação do alerta certo em pelo menos 90%.
- Os critérios que dependiam desses pontos (SC-002, SC-008, SC-013) agora trazem os valores definidos; a sessão também acrescentou SC-015 e SC-016.
- Decisões tomadas por padrão (registradas em Assumptions, revisáveis no plano): tamanho máximo da pergunta de 500 caracteres (FR-024); o país selecionado no mapa não é contexto implícito (FR-013); a conversa some ao recarregar a página.
- Itens adiados para o plano: divisão da cota do serviço de linguagem com a coleta (FR-028); desenho do botão flutuante e convivência com a legenda, o aviso e o painel recolhido da 002; contagem do limite por IP sem guardar o texto da pergunta.
