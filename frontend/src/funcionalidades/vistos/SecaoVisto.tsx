import { IconChevronDown } from "@tabler/icons-react";
import { useId, type ReactNode } from "react";
import { formatarData } from "../../compartilhado/datas";
import { ehUrlWeb } from "../../compartilhado/urlSegura";
import {
  AVISO_DE_FONTE_NAO_OFICIAL,
  AVISO_DE_VISTO_DESATUALIZADO,
  ENTRADA_COM_RG,
  PERMANENCIA_DIVERGENTE,
  PERMANENCIA_VARIA_CONFORME_O_MOTIVO,
  ROTULOS_DE_VISTO,
  TEXTO_NAO_TRADUZIDO,
  TEXTO_SEM_INFORMACAO_DE_VISTO,
  TEXTO_TRADUCAO_AUTOMATICA,
  VARIA_CONFORME_O_MOTIVO,
} from "../../compartilhado/vistos";
import type { ObservacaoDeVisto, Permanencia, Visto } from "../../servicos/api/cliente";

interface Props {
  visto: Visto;
}

/** Texto da fonte quebra em linhas curtas (celular de 360 px) e mantém as quebras de linha dela. */
const CLASSE_DO_TEXTO = "break-words";
const ESTILO_COM_QUEBRAS = { whiteSpace: "pre-line" } as const;

const CLASSE_DA_ETIQUETA = "rounded-full border px-2 py-0.5 text-xs font-semibold";

/** O texto fixo, ou o da fonte (em inglês, sem tradução) quando o formato não é conhecido. */
function TextoDaPermanencia({ permanencia }: { permanencia: Permanencia }) {
  switch (permanencia.tipo) {
    case "varia_conforme_motivo":
      return <span>{PERMANENCIA_VARIA_CONFORME_O_MOTIVO}</span>;
    case "prazos_divergentes":
      return <span>{PERMANENCIA_DIVERGENTE}</span>;
    case "padronizada":
      return <span className={CLASSE_DO_TEXTO}>{permanencia.texto}</span>;
    case "original":
      return (
        <>
          <span lang="en" className={CLASSE_DO_TEXTO}>
            {permanencia.texto}
          </span>{" "}
          <span className="text-xs text-texto-2">({TEXTO_NAO_TRADUZIDO})</span>
        </>
      );
  }
}

function Observacao({ observacao }: { observacao: ObservacaoDeVisto }) {
  if (observacao.traducao === null) {
    return (
      <>
        <p lang="en" className={CLASSE_DO_TEXTO} style={ESTILO_COM_QUEBRAS}>
          {observacao.texto_original}
        </p>
        <p className="text-xs text-texto-2">({TEXTO_NAO_TRADUZIDO})</p>
      </>
    );
  }
  return (
    <>
      <p className={CLASSE_DO_TEXTO} style={ESTILO_COM_QUEBRAS}>
        {observacao.traducao}
      </p>
      <p className="text-xs text-texto-2">({TEXTO_TRADUCAO_AUTOMATICA})</p>
      <details className="group">
        <summary className="flex min-h-11 cursor-pointer list-none items-center gap-1 text-xs font-semibold text-marinho underline">
          Ver o texto original
          <IconChevronDown
            aria-hidden
            size={16}
            className="shrink-0 transition-transform group-open:rotate-180"
          />
        </summary>
        <p lang="en" className={`${CLASSE_DO_TEXTO} pb-2`} style={ESTILO_COM_QUEBRAS}>
          {observacao.texto_original}
        </p>
      </details>
    </>
  );
}

function Observacoes({ observacoes }: { observacoes: readonly ObservacaoDeVisto[] }) {
  if (observacoes.length === 0) return null;
  return (
    <div>
      <p className="text-sm font-semibold">Observações</p>
      <ul>
        {observacoes.map((observacao, indice) => (
          <li key={indice} className="space-y-0.5 border-t border-linha py-2 text-sm">
            <Observacao observacao={observacao} />
          </li>
        ))}
      </ul>
    </div>
  );
}

/** "Fonte: Wikipédia: … (CC BY-SA), dado de 23/10/2026", com o link só se o endereço for web. */
function LinhaDaFonte({ visto }: { visto: Visto }) {
  const { fonte, dado_de: dadoDe } = visto;
  return (
    <p className="text-xs text-texto-2">
      Fonte:{" "}
      {ehUrlWeb(fonte.url) ? (
        <a
          href={fonte.url}
          target="_blank"
          rel="noopener noreferrer"
          className={`${CLASSE_DO_TEXTO} text-marinho underline`}
        >
          {fonte.nome}
        </a>
      ) : (
        fonte.nome
      )}
      {fonte.licenca ? ` (${fonte.licenca})` : ""}
      {dadoDe !== null && (
        <>
          , dado de <time dateTime={dadoDe}>{formatarData(dadoDe)}</time>
        </>
      )}
    </p>
  );
}

function ComDado({ visto }: { visto: Visto }) {
  return (
    <>
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-semibold">{ROTULOS_DE_VISTO[visto.situacao]}</span>
        {visto.aceita_rg && (
          <span className={`${CLASSE_DA_ETIQUETA} border-marinho text-marinho`}>
            {ENTRADA_COM_RG}
          </span>
        )}
      </p>

      {visto.rotulo_original !== null && (
        <p className="text-sm text-texto-2">
          Na fonte:{" "}
          <span lang="en" className={CLASSE_DO_TEXTO}>
            {visto.rotulo_original}
          </span>
        </p>
      )}

      {visto.varia_conforme_motivo && (
        <p>
          <span className={`${CLASSE_DA_ETIQUETA} border-linha`}>{VARIA_CONFORME_O_MOTIVO}</span>
        </p>
      )}

      {visto.permanencia !== null && (
        <p className="text-sm">
          <strong>Permanência:</strong> <TextoDaPermanencia permanencia={visto.permanencia} />
        </p>
      )}

      {visto.origem === "soberano" && (
        <p className="text-sm">
          <span>Sem entrada própria na fonte para este território.</span>{" "}
          <span className={CLASSE_DO_TEXTO}>
            {visto.soberano_nome === null
              ? "Vale a entrada do soberano."
              : `Vale a entrada do soberano: ${visto.soberano_nome}.`}
          </span>
        </p>
      )}

      <Observacoes observacoes={visto.observacoes} />
    </>
  );
}

function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="min-w-0 space-y-2">
      <h3
        id={id}
        className={`${CLASSE_DO_TEXTO} text-sm font-semibold uppercase tracking-wide text-texto-2`}
      >
        {titulo}
      </h3>
      {children}
    </section>
  );
}

/**
 * Seção "Visto" do painel (FR-001 a FR-015): a categoria (sempre em texto), a permanência, as
 * observações, a fonte com a data do dado deste país e o aviso de que não é oficial. Todo texto da
 * fonte ou da tradução entra como texto do React, nunca como HTML (FR-017). O Brasil não tem
 * seção: quem monta o painel não chama este componente quando `visto` é nulo.
 */
export function SecaoVisto({ visto }: Props) {
  const titulo = visto.territorio_nome === null ? "Visto" : `Visto: ${visto.territorio_nome}`;
  const semInformacao = visto.situacao === "sem_informacao";

  return (
    <Secao titulo={titulo}>
      {semInformacao ? (
        <>
          <p className="font-semibold">{ROTULOS_DE_VISTO.sem_informacao}</p>
          <p className="text-sm">{TEXTO_SEM_INFORMACAO_DE_VISTO}</p>
        </>
      ) : (
        <ComDado visto={visto} />
      )}

      {visto.desatualizado && (
        <p className="rounded-lg border border-aviso-borda bg-aviso-fundo p-2 text-sm text-aviso-texto">
          {AVISO_DE_VISTO_DESATUALIZADO}
        </p>
      )}

      {!semInformacao && <LinhaDaFonte visto={visto} />}
      <p className="text-xs text-texto-2">{AVISO_DE_FONTE_NAO_OFICIAL}</p>
    </Secao>
  );
}
