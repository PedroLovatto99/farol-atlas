# Specification Quality Checklist: Requisitos de visto para brasileiros, por país

**Purpose**: Validar a completude e a qualidade da especificação antes de seguir para o planejamento
**Created**: 2026-10-27
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
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

- Os 4 marcadores [NEEDS CLARIFICATION] (FR-007, FR-010, FR-015 e FR-021) foram resolvidos em 2026-10-27 e as respostas estão na seção "Clarifications" da spec. O FR-007a (nota "Varia conforme o motivo da viagem") veio de um ajuste do pedido.
- Revisão de 2026-10-27 (quatro ajustes): "Outra situação" em qualquer parte de um rótulo combinado vale para o país inteiro (FR-007); campo de permanência com "Varia conforme o motivo (ver observações)" (FR-007a); mesma unidade, países reconhecidos, nos dois critérios de coleta válida (FR-010); SC-001 fixo em 95%, medido na primeira coleta válida sobre os países clicáveis, sem o Brasil e as áreas neutras.
- Segunda revisão: no SC-001, "Outra situação" só conta quando vem de rótulo conhecido mapeado de propósito; por rótulo desconhecido não conta (lacuna do dicionário). A entidade de visto registra o motivo de "Outra situação"; rótulos desconhecidos vão para a lista de revisão (FR-012a); novo SC-010: nenhum rótulo desconhecido pendente ao concluir a feature.
- Itens "no implementation details": a spec cita a Wikipédia, a licença CC BY-SA e o `robots.txt` (herdado da constituição) porque são parte do pedido, e não escolhas de implementação.
