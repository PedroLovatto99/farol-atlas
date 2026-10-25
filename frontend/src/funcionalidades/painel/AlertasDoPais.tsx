import { useId } from "react";
import { formatarData } from "../../compartilhado/datas";
import { ehUrlWeb } from "../../compartilhado/urlSegura";
import type { AlertaDoPais } from "../../servicos/api/cliente";

interface Props {
  alertas: readonly AlertaDoPais[];
}

function Titulo({ alerta }: { alerta: AlertaDoPais }) {
  if (!ehUrlWeb(alerta.url)) return <span className="font-semibold">{alerta.titulo}</span>;
  return (
    <a
      href={alerta.url}
      target="_blank"
      rel="noopener noreferrer"
      className="font-semibold text-marinho underline"
    >
      {alerta.titulo}
    </a>
  );
}

/**
 * Todos os alertas de viagem que citam o país, do mais recente ao mais antigo, cada um com data e
 * link para o original no gov.br. Marca o que define o nível exibido (FR-010).
 */
export function AlertasDoPais({ alertas }: Props) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="space-y-1">
      <h3 id={id} className="text-sm font-semibold uppercase tracking-wide text-texto-2">
        Alertas do Itamaraty
      </h3>
      {alertas.length === 0 ? (
        <p className="text-sm text-texto-2">Nenhum alerta de viagem do Itamaraty cita este país.</p>
      ) : (
        <ul>
          {alertas.map((alerta) => (
            <li key={alerta.url} className="space-y-0.5 border-t border-linha py-2 text-sm">
              <Titulo alerta={alerta} />
              <p className="flex flex-wrap items-center gap-x-2 text-xs text-texto-2">
                <time dateTime={alerta.publicado_em}>{formatarData(alerta.publicado_em)}</time>
                {alerta.modificado_em !== null && (
                  <span>Modificado em {formatarData(alerta.modificado_em)}</span>
                )}
              </p>
              <p className="flex flex-wrap gap-1.5 text-xs font-semibold">
                {alerta.define_nivel && (
                  <span className="rounded-full border border-marinho px-2 py-0.5 text-marinho">
                    Define o nível atual
                  </span>
                )}
                {alerta.situacao_normalizada && (
                  <span className="rounded-full border border-linha px-2 py-0.5">
                    Situação normalizada
                  </span>
                )}
                {alerta.pendente === true && (
                  <span className="rounded-full border border-aviso-borda bg-aviso-fundo px-2 py-0.5 text-aviso-texto">
                    Ainda não classificado: confira o alerta original
                  </span>
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
