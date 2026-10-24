import { useMemo, type ComponentType } from "react";
import { NIVEL_PADRAO, type NivelId } from "./compartilhado/niveis";
import { useMovimentoReduzido } from "./compartilhado/useMovimentoReduzido";
import { useTelaPequena } from "./compartilhado/useTelaPequena";
import { ProvedorDeEstado, useEstado } from "./estado/contexto";
import { Aviso } from "./funcionalidades/aviso/Aviso";
import { Legenda } from "./funcionalidades/legenda/Legenda";
import { bordaRegionalDe } from "./funcionalidades/mapa/cor";
import type { MapaProps, PedidoDeCamera, TerritorioDesenhado } from "./funcionalidades/mapa/tipos";
import { useMapa } from "./funcionalidades/mapa/useMapa";
import { Sobre } from "./funcionalidades/sobre/Sobre";
import type { ClienteDaApi, Mapa } from "./servicos/api/cliente";

interface Props {
  cliente: ClienteDaApi;
  /** O componente de mapa (o adaptador do MapLibre; nos testes, um falso). */
  Mapa: ComponentType<MapaProps>;
}

const CAMERA_DO_MUNDO: PedidoDeCamera = { tipo: "mundo" };
const SEM_POSTOS: MapaProps["postos"] = [];
const SEM_PAISES_SEM_POSTO: MapaProps["paisesSemPosto"] = [];

/**
 * Sem coleta completa nada foi confirmado: todo território fica "não verificado", mesmo que a
 * resposta traga outra coisa (princípio V e FR-002).
 */
function territoriosDesenhados(mapa: Mapa): TerritorioDesenhado[] {
  return mapa.territorios.map((t) => ({
    codigo: t.codigo,
    nivel: mapa.dados_obtidos ? t.nivel : NIVEL_PADRAO,
    bordaRegional: mapa.dados_obtidos ? bordaRegionalDe(t.regioes) : null,
    esmaecido: false,
  }));
}

function Tela({ cliente, Mapa: ComponenteDeMapa }: Props) {
  const { estado, tentarDeNovo } = useMapa(cliente);
  const { estado: selecao, despachar } = useEstado();
  const reduzirMovimento = useMovimentoReduzido();
  const celular = useTelaPequena();

  const mapa = estado.situacao === "pronto" ? estado.mapa : null;
  const territorios = useMemo(() => (mapa ? territoriosDesenhados(mapa) : []), [mapa]);

  return (
    <div className="relative h-dvh w-full overflow-hidden bg-espaco text-texto">
      <ComponenteDeMapa
        territorios={territorios}
        postos={SEM_POSTOS}
        paisesSemPosto={SEM_PAISES_SEM_POSTO}
        selecionado={selecao.selecionado}
        grupoEmDestaque={selecao.grupoEmDestaque}
        reduzirMovimento={reduzirMovimento}
        onSelecionarTerritorio={(codigo) => despachar({ tipo: "selecionar", codigo })}
        onSelecionarGrupo={() => {}}
        onLimparSelecao={() => despachar({ tipo: "limpar-selecao" })}
        camera={CAMERA_DO_MUNDO}
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
        <Legenda />
      </details>

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
