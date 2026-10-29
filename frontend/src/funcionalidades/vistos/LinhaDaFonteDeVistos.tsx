import { formatarData } from "../../compartilhado/datas";
import { ehUrlWeb } from "../../compartilhado/urlSegura";
import type { EstadoDosVistos } from "../../estado/reducer";

interface Props {
  estado: EstadoDosVistos;
}

/**
 * "Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em DD/MM/AAAA" (FR-029): a fonte, o
 * aviso e a data da última coleta válida, visíveis também com a legenda recolhida. Sem coleta
 * válida ou com a busca falha, diz isso em vez de mostrar uma data.
 */
export function LinhaDaFonteDeVistos({ estado }: Props) {
  return (
    <p className="rounded-lg border border-linha bg-white px-2 py-1 text-xs leading-snug text-texto-2 shadow-sm">
      <Conteudo estado={estado} />
    </p>
  );
}

function Conteudo({ estado }: Props) {
  if (estado.situacao === "erro") return <>Vistos: dados indisponíveis no momento</>;
  if (estado.situacao !== "pronto") return <>Vistos: carregando…</>;

  const { dados } = estado;
  if (!dados.dados_obtidos || dados.coletado_em === null) {
    return <>Vistos: ainda não há dados de visto</>;
  }
  const { fonte } = dados;
  return (
    <>
      Vistos:{" "}
      {ehUrlWeb(fonte.url) ? (
        <a
          href={fonte.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-marinho underline"
        >
          Wikipédia
        </a>
      ) : (
        "Wikipédia"
      )}
      {fonte.licenca ? ` (${fonte.licenca})` : ""}, fonte não oficial, coletados em{" "}
      {formatarData(dados.coletado_em)}
    </>
  );
}
