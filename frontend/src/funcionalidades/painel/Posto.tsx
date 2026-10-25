import { IconChevronDown, IconMap2 } from "@tabler/icons-react";
import { formatarData } from "../../compartilhado/datas";
import { ehUrlWeb } from "../../compartilhado/urlSegura";
import type { PostoNoPainel } from "../../servicos/api/cliente";
import { urlDoGoogleMaps } from "./googleMaps";

interface Props {
  posto: PostoNoPainel;
  /** No posto responsável o país vem junto da cidade, porque fica fora do país do painel. */
  mostrarPais?: boolean;
}

/** Só vira link de telefone o que parece um único número; o resto fica como texto. */
const PARECE_UM_TELEFONE = /^\+?[\d\s().-]{6,}$/;

function Telefone({ texto }: { texto: string }) {
  if (!PARECE_UM_TELEFONE.test(texto)) return <>{texto}</>;
  return (
    <a href={`tel:${texto.replace(/[^\d+]/g, "")}`} className="text-marinho underline">
      {texto}
    </a>
  );
}

/**
 * Um posto brasileiro, expansível para endereço, telefone de plantão e o link do Google Maps
 * (FR-011, FR-012). Endereço e telefone mostram a própria fonte e a data da coleta (princípio V).
 * Todo texto entra como texto do React, nunca como HTML.
 */
export function Posto({ posto, mostrarPais = false }: Props) {
  const temContato = posto.endereco !== null || posto.telefone_plantao !== null;
  const fonteSegura = posto.contato_fonte_url !== null && ehUrlWeb(posto.contato_fonte_url);

  return (
    <details className="group border-t border-linha">
      <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 py-2 text-sm">
        <span className="font-semibold">{posto.tipo}</span>
        <span className="min-w-0 flex-1 text-texto-2">
          {mostrarPais ? `${posto.cidade}, ${posto.pais}` : posto.cidade}
        </span>
        <IconChevronDown
          aria-hidden
          size={18}
          className="shrink-0 text-texto-2 transition-transform group-open:rotate-180"
        />
      </summary>

      <div className="space-y-2 pb-3 pl-1 text-sm">
        {posto.endereco !== null ? (
          <p>
            <strong>Endereço:</strong> {posto.endereco}
          </p>
        ) : (
          <p className="text-texto-2">Endereço ainda não cadastrado.</p>
        )}

        {posto.telefone_plantao !== null ? (
          <p>
            <strong>Telefone de plantão:</strong> <Telefone texto={posto.telefone_plantao} />
          </p>
        ) : (
          <p className="text-texto-2">Telefone de plantão ainda não cadastrado.</p>
        )}

        {temContato && posto.contato_coletado_em !== null && (
          <p className="text-xs text-texto-2">
            {fonteSegura && posto.contato_fonte_url !== null ? (
              <>
                <a
                  href={posto.contato_fonte_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                >
                  Fonte
                </a>
                , coletado em {formatarData(posto.contato_coletado_em)}
              </>
            ) : (
              <>Coletado em {formatarData(posto.contato_coletado_em)}</>
            )}
          </p>
        )}

        <a
          href={urlDoGoogleMaps(posto)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-11 items-center gap-2 font-semibold text-marinho underline"
        >
          <IconMap2 aria-hidden size={18} />
          Abrir no Google Maps
        </a>
      </div>
    </details>
  );
}
