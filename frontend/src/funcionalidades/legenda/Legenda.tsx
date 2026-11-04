import type { CSSProperties } from "react";
import { NIVEIS, ORDEM_DA_LEGENDA, type NivelId } from "../../compartilhado/niveis";
import { paletaDe } from "../mapa/cor";
import { amostraDaBorda, amostraDoPadrao } from "../mapa/padroes";
import { SobreFronteiras } from "./SobreFronteiras";

interface Props {
  niveisMarcados: readonly NivelId[];
  onAlternarNivel(nivel: NivelId): void;
  daltonismo?: boolean;
}

/** A cor do nível e, no modo daltonismo, o padrão de "não viaje" e "evite", iguais aos do mapa. */
function estiloDaAmostra(nivel: NivelId, daltonismo: boolean): CSSProperties {
  const backgroundColor = paletaDe(daltonismo).niveis[nivel];
  if (daltonismo && (nivel === "nao_viajar" || nivel === "evitar")) {
    return { backgroundColor, ...amostraDoPadrao(nivel) };
  }
  return { backgroundColor };
}

/**
 * Legenda em texto: a cor sozinha nunca é a informação (FR-003). Também é o filtro por nível: uma
 * caixa de marcar por nível, com o rótulo em texto (FR-024).
 */
export function Legenda({ niveisMarcados, onAlternarNivel, daltonismo = false }: Props) {
  const { bordas } = paletaDe(daltonismo);
  return (
    <section
      aria-label="Legenda"
      className="rounded-xl border border-linha bg-white p-3 text-sm leading-snug shadow-sm"
    >
      <ul className="space-y-1.5">
        {ORDEM_DA_LEGENDA.map((nivel) => (
          <li key={nivel}>
            <label className="flex min-h-11 cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={niveisMarcados.includes(nivel)}
                onChange={() => onAlternarNivel(nivel)}
                className="h-5 w-5 shrink-0 accent-marinho"
              />
              <span
                data-amostra
                aria-hidden="true"
                className="h-3 w-[18px] shrink-0 rounded-sm"
                style={estiloDaAmostra(nivel, daltonismo)}
              />
              <span>{NIVEIS[nivel].rotulo}</span>
            </label>
          </li>
        ))}
        <li className="flex items-start gap-2">
          {daltonismo ? (
            <span
              data-amostra
              aria-hidden="true"
              className="mt-0.5 shrink-0"
              style={amostraDaBorda()}
            />
          ) : (
            <span
              data-amostra
              aria-hidden="true"
              className="mt-0.5 h-3 w-[18px] shrink-0 rounded-sm border-2 bg-white"
              style={{
                borderTopColor: bordas.nao_viajar,
                borderRightColor: bordas.nao_viajar,
                borderBottomColor: bordas.evitar,
                borderLeftColor: bordas.evitar,
              }}
            />
          )}
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
