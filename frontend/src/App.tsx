import { useCallback, useEffect, useMemo, useState, type ComponentType } from "react";
import { NIVEL_PADRAO, type NivelId } from "./compartilhado/niveis";
import { useMovimentoReduzido } from "./compartilhado/useMovimentoReduzido";
import { useTelaPequena } from "./compartilhado/useTelaPequena";
import { ProvedorDeEstado, useEstado } from "./estado/contexto";
import { Aviso } from "./funcionalidades/aviso/Aviso";
import { Busca } from "./funcionalidades/busca/Busca";
import { nenhumNivelMarcado, territorioEsmaecido } from "./funcionalidades/legenda/filtro";
import { Legenda } from "./funcionalidades/legenda/Legenda";
import { SemNiveisMarcados } from "./funcionalidades/legenda/SemNiveisMarcados";
import { bordaRegionalDe } from "./funcionalidades/mapa/cor";
import { calcularEnquadramento, margemDoLayout } from "./funcionalidades/mapa/enquadramento";
import { agruparPostos, paisesSemPostoDesenhados } from "./funcionalidades/mapa/marcadores";
import { responsavelDe } from "./funcionalidades/mapa/responsavel";
import type { MapaProps, PedidoDeCamera, TerritorioDesenhado } from "./funcionalidades/mapa/tipos";
import { useGeometria } from "./funcionalidades/mapa/useGeometria";
import { useMapa } from "./funcionalidades/mapa/useMapa";
import { Painel } from "./funcionalidades/painel/Painel";
import { usePais } from "./funcionalidades/painel/usePais";
import { Sobre } from "./funcionalidades/sobre/Sobre";
import type { ClienteDaApi, Mapa, PostoNoPainel } from "./servicos/api/cliente";

interface Props {
  cliente: ClienteDaApi;
  /** O componente de mapa (o adaptador do MapLibre; nos testes, um falso). */
  Mapa: ComponentType<MapaProps>;
  /** Como buscar o arquivo de geometria (nos testes, um falso). Padrão: `fetch`. */
  buscar?: typeof fetch;
}

const CAMERA_INICIAL: PedidoDeCamera = { tipo: "mundo" };
/** Sem geometria carregada não há o que enquadrar: a câmera fica onde está. */
const CAMERA_PARADA: PedidoDeCamera = { tipo: "manter" };
const SEM_POSTOS: MapaProps["postos"] = [];
const SEM_PAISES_SEM_POSTO: MapaProps["paisesSemPosto"] = [];
const SEM_GRUPOS: readonly string[] = [];
const SEM_TERRITORIOS: Mapa["territorios"] = [];

/**
 * Sem coleta completa nada foi confirmado: todo território fica "não verificado", mesmo que a
 * resposta traga outra coisa (princípio V e FR-002). O filtro da legenda age sobre esse mesmo
 * nível, o que o mapa mostra.
 */
function territoriosDesenhados(
  mapa: Mapa,
  niveisMarcados: readonly NivelId[],
): TerritorioDesenhado[] {
  return mapa.territorios.map((t) => {
    const nivel = mapa.dados_obtidos ? t.nivel : NIVEL_PADRAO;
    const regioes = mapa.dados_obtidos ? t.regioes : [];
    return {
      codigo: t.codigo,
      nivel,
      bordaRegional: bordaRegionalDe(regioes),
      esmaecido: territorioEsmaecido({ nivel, regioes }, niveisMarcados),
    };
  });
}

function Tela({ cliente, Mapa: ComponenteDeMapa, buscar }: Props) {
  const { estado, tentarDeNovo } = useMapa(cliente);
  const { estado: selecao, despachar } = useEstado();
  const reduzirMovimento = useMovimentoReduzido();
  const celular = useTelaPequena();
  const geometria = useGeometria(buscar);
  const { estado: estadoDoPais, tentarDeNovo: tentarPaisDeNovo } = usePais(
    cliente,
    selecao.selecionado,
  );
  // O pedido fica no estado: cada toque cria um objeto novo e o mapa o executa de novo, mesmo que
  // a pessoa tenha movido o mapa e toque no mesmo país outra vez.
  const [camera, setCamera] = useState<PedidoDeCamera>(CAMERA_INICIAL);

  const mapa = estado.situacao === "pronto" ? estado.mapa : null;
  const niveisMarcados = selecao.niveisMarcados;
  const territorios = useMemo(
    () => (mapa ? territoriosDesenhados(mapa, niveisMarcados) : []),
    [mapa, niveisMarcados],
  );
  const postos = useMemo(() => (mapa ? agruparPostos(mapa.postos) : SEM_POSTOS), [mapa]);
  const paisesSemPosto = useMemo(
    () => (mapa ? paisesSemPostoDesenhados(mapa) : SEM_PAISES_SEM_POSTO),
    [mapa],
  );
  // Os ícones dos postos que o painel lista aparecem em qualquer zoom, e só quando o painel já chegou
  const gruposDoPainel = useMemo(() => {
    if (estadoDoPais.situacao !== "pronto") return SEM_GRUPOS;
    const { postos: doPais, posto_responsavel: responsavel } = estadoDoPais.pais;
    return [...doPais, ...(responsavel === null ? [] : [responsavel])].map((p) => p.grupo);
  }, [estadoDoPais]);

  const selecionar = useCallback(
    (codigo: string) => {
      // Só países e dependências de /mapa abrem painel; área neutra e códigos desconhecidos não (FR-016)
      if (mapa === null || !mapa.territorios.some((t) => t.codigo === codigo)) return;
      despachar({ tipo: "selecionar", codigo });
      const enquadramento =
        geometria.situacao === "pronto"
          ? calcularEnquadramento({
              geometria: geometria.geometria,
              codigo,
              responsavel: responsavelDe(mapa, codigo),
              margem: margemDoLayout(celular, window.innerHeight),
            })
          : null;
      setCamera(enquadramento ?? CAMERA_PARADA);
    },
    [mapa, geometria, celular, despachar],
  );

  /** Toque num ícone de posto (FR-018g): abre o painel do país do posto, sem reenquadrar o mapa. */
  const tocarIcone = useCallback(
    (grupo: string) => {
      const doGrupo = mapa?.postos.filter((p) => p.grupo === grupo) ?? [];
      const primeiro = doGrupo[0];
      if (primeiro === undefined) return;
      despachar({
        tipo: "tocar-icone",
        territorio: primeiro.territorio,
        grupo,
        ids: doGrupo.map((p) => p.id),
      });
      setCamera(CAMERA_PARADA);
    },
    [mapa, despachar],
  );

  /**
   * Expandir ou recolher um posto no painel (inclusive o responsável): o ícone dele fica em
   * destaque no mapa, e o mapa só anda se o ícone estiver fora da área visível (FR-018a, FR-018c).
   */
  const alternarPosto = useCallback(
    (posto: PostoNoPainel, aberto: boolean) => {
      if (!aberto) return despachar({ tipo: "recolher-posto", id: posto.id, grupo: posto.grupo });
      // O navegador repete o evento quando o posto abre por código (toque no ícone): nada a fazer
      if (selecao.postosExpandidos.includes(posto.id) && selecao.grupoEmDestaque === posto.grupo) {
        return;
      }
      despachar({ tipo: "expandir-posto", id: posto.id, grupo: posto.grupo });
      const noMapa = mapa?.postos.find((p) => p.id === posto.id);
      if (noMapa === undefined) return;
      setCamera({
        tipo: "garantir-visivel",
        latitude: noMapa.latitude,
        longitude: noMapa.longitude,
        margem: margemDoLayout(celular, window.innerHeight),
      });
    },
    [mapa, selecao.postosExpandidos, selecao.grupoEmDestaque, celular, despachar],
  );

  /** "Ver mundo" e Esc: fecha o painel e devolve a câmera ao mundo. */
  const verMundo = useCallback(() => {
    despachar({ tipo: "limpar-selecao" });
    setCamera({ tipo: "mundo" });
  }, [despachar]);

  /** Toque no oceano: fecha o painel, sem mexer na câmera. */
  const limparSelecao = useCallback(() => {
    despachar({ tipo: "limpar-selecao" });
    setCamera(CAMERA_PARADA);
  }, [despachar]);

  const painelAberto = selecao.selecionado !== null && estadoDoPais.situacao !== "ocioso";
  const modoDoPainel = celular ? "gaveta" : "lateral";

  useEffect(() => {
    if (!painelAberto) return;
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key !== "Escape") return;
      // Com um diálogo aberto (Sobre, fronteiras), o Esc é dele
      if (document.querySelector('[role="dialog"]') !== null) return;
      verMundo();
    }
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [painelAberto, verMundo]);

  return (
    <div
      className="relative h-dvh w-full overflow-hidden bg-espaco text-texto"
      data-painel-aberto={painelAberto}
      data-modo-do-painel={modoDoPainel}
    >
      <ComponenteDeMapa
        territorios={territorios}
        postos={postos}
        paisesSemPosto={paisesSemPosto}
        selecionado={selecao.selecionado}
        grupoEmDestaque={selecao.grupoEmDestaque}
        gruposDoPainel={gruposDoPainel}
        reduzirMovimento={reduzirMovimento}
        onSelecionarTerritorio={selecionar}
        onSelecionarGrupo={tocarIcone}
        onLimparSelecao={limparSelecao}
        camera={camera}
      />

      <header className="pointer-events-none absolute inset-x-0 top-0 z-10 flex flex-col gap-2 p-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="pointer-events-auto flex max-w-xl flex-col gap-1">
          <h1 className="text-base font-semibold drop-shadow-sm">Farol Atlas</h1>
          <Aviso
            dadosObtidos={mapa?.dados_obtidos ?? false}
            atualizadoEm={mapa?.atualizado_em ?? null}
            desatualizado={mapa?.desatualizado ?? false}
            carregando={estado.situacao === "carregando"}
          />
          <Busca territorios={mapa?.territorios ?? SEM_TERRITORIOS} onEscolher={selecionar} />
        </div>
        <div className="pointer-events-auto self-end sm:self-auto">
          <Sobre />
        </div>
      </header>

      <details
        open={!celular}
        className="absolute bottom-10 left-2 z-10 max-w-[calc(100%-1rem)] sm:max-w-xs"
      >
        <summary className="flex min-h-11 cursor-pointer list-none items-center rounded-xl border border-linha bg-white px-3 text-sm font-semibold shadow-sm sm:hidden">
          Legenda
        </summary>
        <Legenda
          niveisMarcados={niveisMarcados}
          onAlternarNivel={(nivel) => despachar({ tipo: "alternar-nivel", nivel })}
        />
      </details>

      {estadoDoPais.situacao !== "ocioso" && (
        <Painel
          estado={estadoDoPais}
          onFechar={verMundo}
          onTentarDeNovo={tentarPaisDeNovo}
          modo={modoDoPainel}
          postosExpandidos={selecao.postosExpandidos}
          onAlternarPosto={alternarPosto}
        />
      )}

      {mapa !== null && nenhumNivelMarcado(niveisMarcados) && (
        <SemNiveisMarcados onMarcarTodos={() => despachar({ tipo: "marcar-todos-niveis" })} />
      )}

      {estado.situacao === "carregando" && (
        <p
          role="status"
          className="absolute left-1/2 top-1/2 z-10 -translate-x-1/2 rounded-lg bg-white px-4 py-2 text-sm shadow"
        >
          Carregando os dados do mapa…
        </p>
      )}
      {estado.situacao === "erro" && (
        <div
          role="alert"
          className="absolute left-1/2 top-1/2 z-10 w-[min(90vw,24rem)] -translate-x-1/2 space-y-2 rounded-lg bg-white p-4 text-sm shadow"
        >
          <p>{estado.mensagem}</p>
          <p className="text-texto-2">
            Enquanto isso, todos os países aparecem como não verificado.
          </p>
          <button
            type="button"
            onClick={tentarDeNovo}
            className="min-h-11 rounded-lg bg-marinho px-4 font-semibold text-white"
          >
            Tentar de novo
          </button>
        </div>
      )}
    </div>
  );
}

export default function App(props: Props) {
  return (
    <ProvedorDeEstado>
      <Tela {...props} />
    </ProvedorDeEstado>
  );
}

export type { NivelId };
