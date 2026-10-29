import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import {
  COR_DA_BORDA_DA_AMOSTRA,
  COR_DO_BRASIL_NO_MODO_VISTOS,
  CORES_DE_VISTO,
  ROTULOS_DA_LEGENDA_DE_VISTOS,
  TEXTO_DO_BRASIL_NA_LEGENDA,
  type ChaveDeVisto,
} from "../../compartilhado/vistos";
import type { EstadoDosVistos } from "../../estado/reducer";
import { estadoDoIsento } from "../legenda/filtroDeVistos";
import { SobreFronteiras } from "../legenda/SobreFronteiras";
import { amostraListrada } from "../mapa/padroes";

interface Props {
  estado: EstadoDosVistos;
  marcadas: readonly ChaveDeVisto[];
  onAlternar(chave: ChaveDeVisto): void;
  onTentarDeNovo(): void;
}

/** A amostra de cor: sempre com borda de contraste e escondida do leitor de tela (o texto diz tudo). */
function Amostra({ estilo }: { estilo: CSSProperties }) {
  return (
    <span
      data-amostra
      aria-hidden="true"
      className="h-3 w-[18px] shrink-0 rounded-sm border"
      style={{ borderColor: COR_DA_BORDA_DA_AMOSTRA, ...estilo }}
    />
  );
}

function estiloDaAmostra(chave: ChaveDeVisto): CSSProperties {
  if (chave === "isento_rg") return amostraListrada();
  return { backgroundColor: CORES_DE_VISTO[chave] };
}

interface CaixaProps {
  chave: ChaveDeVisto;
  marcada: boolean;
  misto?: boolean;
  onAlternar(chave: ChaveDeVisto): void;
}

/** Caixa de marcar com o rótulo em texto; o estado misto vai por `aria-checked` e por "(parcial)". */
function Caixa({ chave, marcada, misto = false, onAlternar }: CaixaProps) {
  const entrada = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (entrada.current !== null) entrada.current.indeterminate = misto;
  }, [misto]);

  return (
    <label className="flex min-h-11 cursor-pointer items-center gap-2">
      <input
        ref={entrada}
        type="checkbox"
        checked={marcada}
        aria-checked={misto ? "mixed" : undefined}
        onChange={() => onAlternar(chave)}
        className="h-5 w-5 shrink-0 accent-marinho"
      />
      <Amostra estilo={estiloDaAmostra(chave)} />
      <span>
        {ROTULOS_DA_LEGENDA_DE_VISTOS[chave]}
        {misto && <span className="text-xs text-texto-2"> (parcial)</span>}
      </span>
    </label>
  );
}

function Itens({ marcadas, onAlternar }: Pick<Props, "marcadas" | "onAlternar">) {
  const isento = estadoDoIsento(marcadas);
  const simples = (chave: ChaveDeVisto) => (
    <li key={chave}>
      <Caixa chave={chave} marcada={marcadas.includes(chave)} onAlternar={onAlternar} />
    </li>
  );
  return (
    <ul className="space-y-1.5">
      <li>
        <Caixa
          chave="isento"
          marcada={isento === "marcado"}
          misto={isento === "misto"}
          onAlternar={onAlternar}
        />
        <ul className="ml-7">
          <li>
            <Caixa
              chave="isento_rg"
              marcada={marcadas.includes("isento_rg")}
              onAlternar={onAlternar}
            />
          </li>
        </ul>
      </li>
      {(
        [
          "visto_na_chegada",
          "autorizacao_eletronica",
          "visto_exigido",
          "outra_situacao",
          "sem_informacao",
        ] as const
      ).map(simples)}
      <li className="flex min-h-11 items-center gap-2">
        <span className="h-5 w-5 shrink-0" aria-hidden="true" />
        <Amostra estilo={{ backgroundColor: COR_DO_BRASIL_NO_MODO_VISTOS }} />
        <span>{TEXTO_DO_BRASIL_NA_LEGENDA}</span>
      </li>
    </ul>
  );
}

function Corpo({ estado, marcadas, onAlternar, onTentarDeNovo }: Props): ReactNode {
  if (estado.situacao === "erro") {
    return (
      <div role="alert" className="space-y-2">
        <p>Não foi possível carregar os vistos.</p>
        <button
          type="button"
          onClick={onTentarDeNovo}
          className="min-h-11 rounded-lg bg-marinho px-4 font-semibold text-white"
        >
          Tentar de novo
        </button>
      </div>
    );
  }
  if (estado.situacao !== "pronto") {
    // "nao_pedido" dura só até o pedido sair, logo depois de a pessoa escolher o modo
    return <p role="status">Carregando os vistos…</p>;
  }
  return (
    <>
      {!estado.dados.dados_obtidos && (
        <p className="mb-2 text-xs text-texto-2">
          Ainda não há dados de visto: todos os países aparecem como sem informação de visto.
        </p>
      )}
      <Itens marcadas={marcadas} onAlternar={onAlternar} />
    </>
  );
}

/**
 * Legenda do modo "Vistos": cada categoria em texto, com a cor ao lado, e o filtro por caixa de
 * marcar (FR-024). "Isento, entrada com RG" é um subitem de "Isento de visto" (FR-022a). Carregando
 * e erro mostram só a mensagem, sem itens.
 */
export function LegendaDeVistos(props: Props) {
  return (
    <section
      aria-label="Legenda"
      className="rounded-xl border border-linha bg-white p-3 text-sm leading-snug shadow-sm"
    >
      <Corpo {...props} />
      <SobreFronteiras />
    </section>
  );
}
