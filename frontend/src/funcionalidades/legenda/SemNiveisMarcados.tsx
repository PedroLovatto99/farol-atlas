interface Props {
  onMarcarTodos(): void;
}

/** Aviso sobre o mapa quando o filtro desmarcou todos os níveis, com o botão que desfaz. */
export function SemNiveisMarcados({ onMarcarTodos }: Props) {
  return (
    <div
      role="status"
      className="absolute left-1/2 top-1/2 z-10 w-[min(90vw,24rem)] -translate-x-1/2 -translate-y-1/2 space-y-2 rounded-lg bg-white p-4 text-sm shadow"
    >
      <p>Nenhum nível marcado na legenda. Todos os países estão esmaecidos.</p>
      <button
        type="button"
        onClick={onMarcarTodos}
        className="min-h-11 rounded-lg bg-marinho px-4 font-semibold text-white"
      >
        Marcar todos os níveis
      </button>
    </div>
  );
}
