import { NIVEIS, ORDEM_DA_LEGENDA } from "../../compartilhado/niveis";
import { COR_DA_BORDA_REGIONAL } from "../mapa/cor";
import { SobreFronteiras } from "./SobreFronteiras";

/** Legenda em texto: a cor sozinha nunca é a informação (FR-003). */
export function Legenda() {
  return (
    <section
      aria-label="Legenda"
      className="rounded-xl border border-linha bg-white p-3 text-sm leading-snug shadow-sm"
    >
      <ul className="space-y-1.5">
        {ORDEM_DA_LEGENDA.map((nivel) => (
          <li key={nivel} className="flex items-center gap-2">
            <span
              data-amostra
              aria-hidden="true"
              className="h-3 w-[18px] shrink-0 rounded-sm"
              style={{ backgroundColor: NIVEIS[nivel].cor }}
            />
            <span>{NIVEIS[nivel].rotulo}</span>
          </li>
        ))}
        <li className="flex items-start gap-2">
          <span
            data-amostra
            aria-hidden="true"
            className="mt-0.5 h-3 w-[18px] shrink-0 rounded-sm border-2 bg-white"
            style={{
              borderTopColor: COR_DA_BORDA_REGIONAL.nao_viajar,
              borderRightColor: COR_DA_BORDA_REGIONAL.nao_viajar,
              borderBottomColor: COR_DA_BORDA_REGIONAL.evitar,
              borderLeftColor: COR_DA_BORDA_REGIONAL.evitar,
            }}
          />
          <span>
            Região mais grave
            <span className="block text-xs text-texto-2">
              Borda vermelha: região de “não viaje”. Borda marrom: região de “evite”.
            </span>
          </span>
        </li>
      </ul>
      <p className="mt-2 text-xs text-texto-2">
        Ausência de alerta não significa que o governo recomenda a viagem.
      </p>
      <SobreFronteiras />
    </section>
  );
}
