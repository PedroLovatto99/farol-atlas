interface Props {
  onMarcarTodos(): void;
  /** O que foi desmarcado e o botão que desfaz; o padrão é o dos níveis de alerta (001). */
  mensagem?: string;
  botao?: string;
}

/** Aviso sobre o mapa quando o filtro da legenda desmarcou tudo, com o botão que desfaz. */
export function SemNiveisMarcados({
  onMarcarTodos,
  mensagem = "Nenhum nível marcado na legenda. Todos os países estão esmaecidos.",
  botao = "Marcar todos os níveis",
}: Props) {
  return (
    <div
      role="status"
      className="absolute left-1/2 top-1/2 z-10 w-[min(90vw,24rem)] -translate-x-1/2 -translate-y-1/2 space-y-2 rounded-lg bg-white p-4 text-sm shadow"
    >
      <p>{mensagem}</p>
      <button
        type="button"
        onClick={onMarcarTodos}
        className="min-h-11 rounded-lg bg-marinho px-4 font-semibold text-white"
      >
        {botao}
      </button>
    </div>
  );
}
