import { IconChevronUp, IconWorld } from "@tabler/icons-react";
import { useEffect, useRef } from "react";
import { Bandeira } from "../../compartilhado/Bandeira";
import { ALERTA_SO_REGIONAL, NIVEIS } from "../../compartilhado/niveis";
import { ROTULOS_DE_VISTO } from "../../compartilhado/vistos";
import type { Pais } from "../../servicos/api/cliente";
import type { ModoDoGlobo } from "../mapa/tipos";

interface Props {
  pais: Pais;
  /** O que o globo mostra: a barra diz a situação do mesmo modo. */
  modoDoGlobo: ModoDoGlobo;
  /** Computador: flutua no canto do painel. Celular: no rodapé, em largura total. */
  modo: "lateral" | "gaveta";
  /** Expande o painel de novo. */
  onAlternar(): void;
  /** "Ver mundo": fecha e devolve a câmera ao mundo, como no painel expandido. */
  onFechar(): void;
}

/** Só a posição muda entre os formatos; o resto da barra é o mesmo (FR-030). */
const CLASSES_DO_MODO = {
  lateral: "absolute right-2 top-16 z-20 w-[340px]",
  gaveta: "absolute inset-x-2 bottom-2 z-20",
} as const;

/**
 * A situação principal do país, do que o painel já carregou (não depende de `/vistos`). Nula para
 * o Brasil, que não tem nível nem visto, e para um país sem a seção de visto.
 */
function situacaoDe(pais: Pais, modoDoGlobo: ModoDoGlobo): string | null {
  if (pais.eh_brasil) return null;
  if (modoDoGlobo === "vistos") {
    if (pais.visto === null) return null;
    const rotulo = ROTULOS_DE_VISTO[pais.visto.situacao];
    return pais.visto.territorio_nome === null
      ? rotulo
      : `${pais.visto.territorio_nome}: ${rotulo}`;
  }
  return pais.regiao_unica_do_alerta === true
    ? ALERTA_SO_REGIONAL.rotulo
    : NIVEIS[pais.nivel].rotulo;
}

/**
 * O painel do país recolhido (FR-030): uma barra horizontal com bandeira, nome, situação do modo
 * atual, o botão que expande e o "Ver mundo". Um componente só para o celular e o computador.
 */
export function BarraDoPainel({ pais, modoDoGlobo, modo, onAlternar, onFechar }: Props) {
  const situacao = situacaoDe(pais, modoDoGlobo);
  const botaoDeExpandir = useRef<HTMLButtonElement>(null);

  // A barra aparece por uma ação da pessoa (Recolher painel): o foco acompanha o botão que sumiu
  useEffect(() => {
    botaoDeExpandir.current?.focus({ preventScroll: true });
  }, []);

  return (
    <aside
      aria-label="Detalhes do país (recolhido)"
      data-modo={modo}
      className={`${CLASSES_DO_MODO[modo]} flex min-h-14 items-center gap-1 rounded-2xl border border-linha bg-white p-1 shadow-lg`}
    >
      <button
        ref={botaoDeExpandir}
        type="button"
        aria-expanded="false"
        title={pais.nome}
        aria-label={`Expandir painel: ${pais.nome}${situacao === null ? "" : `, ${situacao}`}`}
        onClick={onAlternar}
        className="flex min-h-11 min-w-0 flex-1 items-center gap-2 rounded-xl px-2 py-1 text-left"
      >
        <Bandeira codigo={pais.bandeira} />
        <span className="min-w-0 flex-1">
          <span title={pais.nome} className="block truncate font-semibold leading-snug">
            {pais.nome}
          </span>
          {situacao !== null && (
            <span data-situacao className="block break-words text-sm leading-snug text-texto-2">
              {situacao}
            </span>
          )}
        </span>
        <IconChevronUp aria-hidden size={18} className="shrink-0" />
      </button>
      <button
        type="button"
        aria-label="Ver mundo"
        onClick={onFechar}
        className="flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-xl border border-linha"
      >
        <IconWorld aria-hidden size={20} />
      </button>
    </aside>
  );
}
