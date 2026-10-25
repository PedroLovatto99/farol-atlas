import { IconWorld } from "@tabler/icons-react";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { Bandeira } from "../../compartilhado/Bandeira";
import { formatarData } from "../../compartilhado/datas";
import { ALERTA_SO_REGIONAL, NIVEIS } from "../../compartilhado/niveis";
import { ehUrlWeb } from "../../compartilhado/urlSegura";
import type { FontePostos, Pais, PostoNoPainel } from "../../servicos/api/cliente";
import { URL_DO_PORTAL_CONSULAR } from "../aviso/Aviso";
import { SobreFronteiras } from "../legenda/SobreFronteiras";
import { COR_DA_BORDA_REGIONAL } from "../mapa/cor";
import { AlertasDoPais } from "./AlertasDoPais";
import { Posto } from "./Posto";
import type { EstadoDoPais } from "./usePais";

interface Props {
  estado: Exclude<EstadoDoPais, { situacao: "ocioso" }>;
  /** Fecha o painel e devolve o mapa à visão do mundo ("Ver mundo"). */
  onFechar(): void;
  onTentarDeNovo(): void;
  /** Computador: painel lateral. Celular: gaveta na parte de baixo. */
  modo?: "lateral" | "gaveta";
  /** Ids dos postos abertos, decididos pela tela: o ícone de cada um acompanha no mapa. */
  postosExpandidos?: readonly number[];
  /** A pessoa expandiu ou recolheu um posto (inclusive o responsável). */
  onAlternarPosto?(posto: PostoNoPainel, aberto: boolean): void;
}

interface ControleDosPostos {
  postosExpandidos: readonly number[] | undefined;
  onAlternarPosto: ((posto: PostoNoPainel, aberto: boolean) => void) | undefined;
}

/** Só controla o posto quando a tela dá o estado; sem ele o posto abre e fecha sozinho. */
function controleDe(
  posto: PostoNoPainel,
  { postosExpandidos, onAlternarPosto }: ControleDosPostos,
) {
  if (postosExpandidos === undefined || onAlternarPosto === undefined) return {};
  return {
    aberto: postosExpandidos.includes(posto.id),
    onAlternar: (aberto: boolean) => onAlternarPosto(posto, aberto),
  };
}

const CLASSES_DO_MODO = {
  lateral: "absolute bottom-2 right-2 top-16 z-20 w-[340px] rounded-2xl",
  gaveta: "absolute inset-x-0 bottom-0 z-20 h-[55dvh] rounded-t-2xl",
} as const;

function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="space-y-1">
      <h3 id={id} className="text-sm font-semibold uppercase tracking-wide text-texto-2">
        {titulo}
      </h3>
      {children}
    </section>
  );
}

function Observacao({ texto }: { texto: string }) {
  return (
    <div className="rounded-lg border border-linha bg-espaco p-3 text-sm">
      <p>{texto}</p>
      <SobreFronteiras />
    </div>
  );
}

/** "Itamaraty e Wikipédia (CC BY-SA)", com um link em cada nome (FR-011a). */
function Fontes({ fontes }: { fontes: FontePostos["fontes"] }) {
  return (
    <>
      {fontes.map((fonte, indice) => (
        <span key={fonte.nome}>
          {indice > 0 && (indice === fontes.length - 1 ? " e " : ", ")}
          {ehUrlWeb(fonte.url) ? (
            <a
              href={fonte.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-marinho underline"
            >
              {fonte.nome}
            </a>
          ) : (
            fonte.nome
          )}
          {fonte.licenca ? ` (${fonte.licenca})` : ""}
        </span>
      ))}
    </>
  );
}

function LinhaDaFonte({ fonte }: { fonte: FontePostos }) {
  return (
    <p className="pt-2 text-xs text-texto-2">
      Postos: <Fontes fontes={fonte.fontes} />, conferidos em {formatarData(fonte.conferido_em)}
    </p>
  );
}

function Postos({ pais, controle }: { pais: Pais; controle: ControleDosPostos }) {
  const temPostos = pais.postos.length > 0;
  return (
    <Secao titulo="Representação brasileira">
      {temPostos && (
        <div>
          {pais.postos.map((posto) => (
            <Posto key={posto.id} posto={posto} {...controleDe(posto, controle)} />
          ))}
        </div>
      )}

      {!temPostos && pais.posto_responsavel !== null && (
        <>
          <p className="text-sm">Sem posto no país. O atendimento é feito por:</p>
          <Posto
            posto={pais.posto_responsavel}
            mostrarPais
            {...controleDe(pais.posto_responsavel, controle)}
          />
        </>
      )}

      {pais.sem_posto_indicado && (
        <p className="text-sm">
          Sem posto no país e sem posto indicado na lista oficial. Procure o Itamaraty pelo{" "}
          <a
            href={URL_DO_PORTAL_CONSULAR}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-marinho underline"
          >
            Portal Consular
          </a>
          .
        </p>
      )}

      {pais.fonte_postos !== null && <LinhaDaFonte fonte={pais.fonte_postos} />}
    </Secao>
  );
}

function NivelDoPais({ pais }: { pais: Pais }) {
  const nivel = NIVEIS[pais.nivel];
  // só regional: a cor do swatch segue a do mapa (neutra), mas o título não diz "sem alerta"
  const soRegional = pais.regiao_unica_do_alerta === true;
  return (
    <div className="space-y-1">
      <p className="flex items-center gap-2 font-semibold">
        <span
          aria-hidden="true"
          className="h-3 w-[18px] shrink-0 rounded-sm"
          style={{ backgroundColor: nivel.cor }}
        />
        {soRegional ? ALERTA_SO_REGIONAL.rotulo : nivel.rotulo}
      </p>
      {soRegional ? (
        <>
          <p className="text-sm font-semibold">{ALERTA_SO_REGIONAL.aviso}</p>
          <p className="text-sm text-texto-2">{ALERTA_SO_REGIONAL.texto}</p>
        </>
      ) : (
        <p className="text-sm text-texto-2">{nivel.texto}</p>
      )}
    </div>
  );
}

function Regioes({ pais }: { pais: Pais }) {
  if (pais.regioes.length === 0) return null;
  return (
    <Secao titulo="Alertas regionais">
      <ul>
        {pais.regioes.map((regiao) => (
          <li
            key={regiao.nome}
            className="flex items-center gap-2 border-t border-linha py-2 text-sm"
          >
            <span
              aria-hidden="true"
              className="h-3 w-[18px] shrink-0 rounded-sm border-2 bg-white"
              style={{ borderColor: COR_DA_BORDA_REGIONAL[regiao.nivel] }}
            />
            <span>
              <strong>{regiao.nome}:</strong>{" "}
              {regiao.nivel === "nao_viajar" ? NIVEIS.nao_viajar.rotulo : NIVEIS.evitar.rotulo}
            </span>
          </li>
        ))}
      </ul>
    </Secao>
  );
}

function Conteudo({ pais, controle }: { pais: Pais; controle: ControleDosPostos }) {
  if (pais.eh_brasil) {
    return (
      <p className="text-sm text-texto-2">
        Toque em outro país para ver o alerta e onde fica a representação brasileira mais próxima.
      </p>
    );
  }
  return (
    <>
      {pais.observacao !== null && pais.observacao_no_topo && (
        <Observacao texto={pais.observacao} />
      )}
      <NivelDoPais pais={pais} />
      <Regioes pais={pais} />
      {pais.observacao !== null && !pais.observacao_no_topo && (
        <Observacao texto={pais.observacao} />
      )}
      <AlertasDoPais alertas={pais.alertas} />
      <Postos pais={pais} controle={controle} />
    </>
  );
}

/**
 * Painel do país (FR-009 a FR-015): bandeira, nome, nível, regiões, alertas, postos e posto
 * responsável. Painel lateral no computador e gaveta no celular.
 */
export function Painel({
  estado,
  onFechar,
  onTentarDeNovo,
  modo = "lateral",
  postosExpandidos,
  onAlternarPosto,
}: Props) {
  const pais = estado.situacao === "pronto" ? estado.pais : null;
  const raiz = useRef<HTMLElement>(null);

  // O painel abre por uma ação da pessoa (toque, busca): leva o foco para ele, para o leitor de
  // tela anunciá-lo, e devolve o foco a quem o tinha quando o painel fecha.
  useEffect(() => {
    const quemTinhaOFoco =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    raiz.current?.focus({ preventScroll: true });
    return () => {
      if (quemTinhaOFoco?.isConnected) quemTinhaOFoco.focus({ preventScroll: true });
    };
  }, []);

  return (
    <aside
      ref={raiz}
      tabIndex={-1}
      aria-label="Detalhes do país"
      data-modo={modo}
      className={`${CLASSES_DO_MODO[modo]} flex flex-col overflow-hidden border border-linha bg-white shadow-lg outline-none`}
    >
      <header className="flex items-start gap-2 border-b border-linha p-3">
        {pais !== null ? (
          <>
            <Bandeira codigo={pais.bandeira} />
            <h2 className="min-w-0 flex-1 text-lg font-semibold leading-snug">{pais.nome}</h2>
          </>
        ) : (
          <span className="flex-1" />
        )}
        <button
          type="button"
          onClick={onFechar}
          className="flex min-h-11 shrink-0 items-center gap-1.5 rounded-lg border border-linha px-3 text-sm font-semibold"
        >
          <IconWorld aria-hidden size={18} />
          Ver mundo
        </button>
      </header>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3">
        {estado.situacao === "carregando" && (
          <p role="status" className="text-sm">
            Carregando os dados do país…
          </p>
        )}
        {estado.situacao === "erro" && (
          <div role="alert" className="space-y-2 text-sm">
            <p>{estado.mensagem}</p>
            <button
              type="button"
              onClick={onTentarDeNovo}
              className="min-h-11 rounded-lg bg-marinho px-4 font-semibold text-white"
            >
              Tentar de novo
            </button>
          </div>
        )}
        {pais !== null && <Conteudo pais={pais} controle={{ postosExpandidos, onAlternarPosto }} />}
      </div>
    </aside>
  );
}
