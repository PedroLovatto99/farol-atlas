import { useId, useState } from "react";
import type { NivelId } from "../../compartilhado/niveis";
import { Legenda } from "./Legenda";
import { gravarPreferenciaDaLegenda, lerPreferenciaDaLegenda } from "./preferencia";

interface Props {
  /** Tela estreita (celular): sem escolha guardada, a legenda começa recolhida. */
  telaPequena: boolean;
  niveisMarcados: readonly NivelId[];
  onAlternarNivel(nivel: NivelId): void;
}

/**
 * A legenda com um botão que a recolhe e a mostra. Recolhida, sobra só o botão, para não cobrir o
 * mapa. O filtro por nível mora na tela (`niveisMarcados`), não aqui: recolher não o desfaz.
 * A escolha da pessoa fica guardada entre visitas; sem ela vale a largura da tela.
 */
export function LegendaRecolhivel({ telaPequena, niveisMarcados, onAlternarNivel }: Props) {
  const idDoConteudo = useId();
  const [escolha, setEscolha] = useState<boolean | null>(lerPreferenciaDaLegenda);
  const aberta = escolha ?? !telaPequena;

  function alternar() {
    setEscolha(!aberta);
    gravarPreferenciaDaLegenda(!aberta);
  }

  // coluna invertida: a legenda abre para cima e o botão não sai do lugar
  return (
    <div className="absolute bottom-10 left-2 z-10 flex max-w-[calc(100%-1rem)] flex-col-reverse items-start gap-2 sm:max-w-xs">
      <button
        type="button"
        aria-expanded={aberta}
        aria-controls={idDoConteudo}
        onClick={alternar}
        className="flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-linha bg-white px-3 text-sm font-semibold shadow-sm"
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className={`h-4 w-4 shrink-0 ${aberta ? "" : "rotate-180"}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M5 8l5 5 5-5" />
        </svg>
        Legenda das cores
      </button>
      <div id={idDoConteudo} hidden={!aberta} className="w-full">
        <Legenda niveisMarcados={niveisMarcados} onAlternarNivel={onAlternarNivel} />
      </div>
    </div>
  );
}
