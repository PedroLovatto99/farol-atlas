import type { ModoDoGlobo } from "../mapa/tipos";

interface Props {
  modo: ModoDoGlobo;
  onTrocar(modo: ModoDoGlobo): void;
}

const OPCOES: readonly { modo: ModoDoGlobo; rotulo: string }[] = [
  { modo: "alertas", rotulo: "Alertas" },
  { modo: "vistos", rotulo: "Vistos" },
];

/**
 * Seletor "Alertas | Vistos" (FR-021): dois botões de opção nativos, então o Tab entra no grupo, as
 * setas trocam a opção e o leitor de tela anuncia "1 de 2". A opção ativa tem negrito e fundo
 * escuro, não só cor. Sem transição nem animação.
 */
export function SeletorDeModo({ modo, onTrocar }: Props) {
  return (
    <div
      role="radiogroup"
      aria-label="O que o globo mostra"
      className="inline-flex overflow-hidden rounded-xl border border-linha bg-white shadow-sm"
    >
      {OPCOES.map((opcao) => {
        const ativo = opcao.modo === modo;
        return (
          <label
            key={opcao.modo}
            className={`flex min-h-11 min-w-20 cursor-pointer items-center justify-center px-4 text-sm has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-4 has-[:focus-visible]:outline-aviso-borda ${
              ativo ? "bg-marinho font-semibold text-white" : "text-texto"
            }`}
          >
            <input
              type="radio"
              name="modo-do-globo"
              value={opcao.modo}
              checked={ativo}
              onChange={() => onTrocar(opcao.modo)}
              className="sr-only"
            />
            {opcao.rotulo}
          </label>
        );
      })}
    </div>
  );
}
