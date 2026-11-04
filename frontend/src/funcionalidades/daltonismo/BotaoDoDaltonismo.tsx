interface Props {
  ligado: boolean;
  onAlternar(): void;
}

/**
 * Liga e desliga as paletas acessíveis. O nome é fixo e o estado vai por `aria-pressed`; na tela, o
 * quadradinho marcado e o negrito mostram o estado sem depender da cor (FR-002). Sem animação.
 */
export function BotaoDoDaltonismo({ ligado, onAlternar }: Props) {
  return (
    <button
      type="button"
      aria-pressed={ligado}
      onClick={onAlternar}
      className={`flex min-h-11 cursor-pointer items-center gap-1.5 rounded-xl border border-linha px-2 shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-4 focus-visible:outline-aviso-borda ${
        ligado ? "bg-marinho font-semibold text-white" : "bg-white text-texto"
      }`}
    >
      <span
        aria-hidden="true"
        className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-current"
      >
        {ligado && (
          <svg
            viewBox="0 0 16 16"
            className="h-3 w-3"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 8.5l3.5 3.5L13 4.5" />
          </svg>
        )}
      </span>
      <span className="text-left text-xs leading-tight">
        Modo <br />
        daltonismo
      </span>
    </button>
  );
}
