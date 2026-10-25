/**
 * Adaptador do MapLibre GL JS 6: o ÚNICO arquivo que importa `maplibre-gl` (princípio III).
 * Cumpre `MapaProps`; trocar a biblioteca só mexe aqui.
 *
 * O mapa é um globo 3D só com oceano e países: preenchimento pela cor do nível, fronteiras, borda
 * de destaque das regiões mais graves e contorno do país selecionado. Toque em país seleciona;
 * oceano limpa a seleção; área neutra é ignorada (FR-016). Os ícones dos postos são botões do
 * React, desenhados por portal dentro de marcadores do MapLibre. As regras (quais ícones aparecem,
 * enquadramento, plano de câmera) são funções puras fora daqui; o adaptador só as executa.
 */
import "maplibre-gl/dist/maplibre-gl.css";
import {
  AttributionControl,
  Map as MapaDoMapLibre,
  Marker,
  NavigationControl,
  setWorkerUrl,
  type GeoJSONSource,
  type StyleSpecification,
} from "maplibre-gl";
import urlDoWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { planejarCamera, type ContextoDaCamera } from "./camera";
import { duracaoDoMovimento } from "./enquadramento";
import { montarFeicoes } from "./feicoes";
import { Marcador } from "./Marcador";
import {
  ZOOM_DOS_MARCADORES,
  linhaAteOResponsavel,
  paisesSemPostoVisiveis,
  postosVisiveis,
  rotuloDoGrupo,
  rotuloDoPaisSemPosto,
  seloDoMarcador,
  varianteDoMarcador,
} from "./marcadores";
import type { MapaProps, Margem } from "./tipos";
import { useGeometria } from "./useGeometria";

// O MapLibre 6 lê os mapas num web worker. O Vite (no modo de desenvolvimento) pré-empacota a
// biblioteca e o endereço do worker se perde ("Worker failed to load"): informá-lo aqui funciona
// no desenvolvimento e no build.
setWorkerUrl(urlDoWorker);

const COR_DO_OCEANO = "#DCE8F2";
const COR_DA_SELECAO = "#0C447C";
const COR_DA_LINHA_ATE_O_RESPONSAVEL = "#0C447C";
/** Opacidade de um país esmaecido pelo filtro: ainda se vê a cor do nível e ainda se toca (FR-025). */
const OPACIDADE_ESMAECIDA = 0.25;
const LARGURA_MAXIMA_DO_CELULAR = 700;
const COLECAO_VAZIA = { type: "FeatureCollection" as const, features: [] };

/** Desenha o contorno de todo o grupo de enquadramento; sem seleção, o filtro não casa com nada. */
function filtroDaSelecao(grupo: string | null): ["==", ["get", string], string] {
  return ["==", ["get", "zoom"], grupo ?? ""];
}

/** Só oceano e países, sem mapa de fundo. As cores vêm das propriedades de cada feição. */
const ESTILO: StyleSpecification = {
  version: 8,
  sources: {
    paises: { type: "geojson", data: COLECAO_VAZIA },
    linha: { type: "geojson", data: COLECAO_VAZIA },
  },
  layers: [
    { id: "oceano", type: "background", paint: { "background-color": COR_DO_OCEANO } },
    {
      id: "paises",
      type: "fill",
      source: "paises",
      // Filtro de níveis (FR-025): esmaecer reduz a opacidade e mantém a cor; o toque segue valendo
      paint: {
        "fill-color": ["get", "cor"],
        "fill-opacity": ["case", ["get", "esmaecido"], OPACIDADE_ESMAECIDA, 1],
      },
    },
    {
      id: "fronteiras",
      type: "line",
      source: "paises",
      paint: { "line-color": "#ffffff", "line-width": 0.6 },
    },
    {
      id: "regional",
      type: "line",
      source: "paises",
      filter: ["has", "borda_regional"],
      paint: {
        "line-color": ["get", "borda_regional"],
        "line-width": 2.5,
        "line-opacity": ["case", ["get", "esmaecido"], OPACIDADE_ESMAECIDA, 1],
      },
    },
    {
      // Contorno do país selecionado: o filtro (grupo `zoom`) é trocado em `filtroDaSelecao`
      id: "selecao",
      type: "line",
      source: "paises",
      filter: filtroDaSelecao(null),
      paint: { "line-color": COR_DA_SELECAO, "line-width": 3 },
    },
    {
      // Ligação do ícone do país sem posto até o posto responsável (FR-018)
      id: "linha-responsavel",
      type: "line",
      source: "linha",
      paint: {
        "line-color": COR_DA_LINHA_ATE_O_RESPONSAVEL,
        "line-width": 2,
        "line-dasharray": [2, 2],
      },
    },
  ],
};

function visaoDoMundo(): { center: [number, number]; zoom: number } {
  const celular = window.innerWidth <= LARGURA_MAXIMA_DO_CELULAR;
  return { center: [25, 18], zoom: celular ? 0.85 : 1.75 };
}

/** Onde o ponto está na tela e do que o mapa está olhando, para decidir se precisa mover. */
function medirMapa(mapa: MapaDoMapLibre, longitude: number, latitude: number): ContextoDaCamera {
  const centro = mapa.getCenter();
  const posicao = mapa.project([longitude, latitude]);
  const tela = mapa.getCanvas();
  return {
    centro: { longitude: centro.lng, latitude: centro.lat },
    pontoNaTela: Number.isFinite(posicao.x) && Number.isFinite(posicao.y) ? posicao : null,
    tamanho: { largura: tela.clientWidth, altura: tela.clientHeight },
  };
}

/**
 * Onde o ponto deve cair para ficar na área livre: o deslocamento do centro da tela até o centro
 * do que o painel não cobre. Mover só o centro, sem `padding`, não deixa estado para trás.
 */
function deslocamentoDaAreaLivre(margem: Margem): [number, number] {
  return [(margem.esquerda - margem.direita) / 2, (margem.topo - margem.baixo) / 2];
}

/** Ícone no mapa: um marcador do MapLibre cujo conteúdo é desenhado pelo React (portal). */
function MarcadorNoMapa(props: {
  mapa: MapaDoMapLibre;
  longitude: number;
  latitude: number;
  children: ReactNode;
}) {
  const { mapa, longitude, latitude, children } = props;
  const [elemento] = useState(() => {
    const el = document.createElement("div");
    el.className = "marcador-raiz";
    return el;
  });

  useEffect(() => {
    // `opacityWhenCovered`: ícones do outro lado do globo somem e não recebem toque
    const marcador = new Marker({ element: elemento, anchor: "center", opacityWhenCovered: 0 })
      .setLngLat([longitude, latitude])
      .addTo(mapa);
    return () => {
      marcador.remove();
    };
  }, [mapa, elemento, longitude, latitude]);

  return createPortal(children, elemento);
}

export function MapaMapLibre({
  territorios,
  postos,
  paisesSemPosto,
  selecionado,
  grupoEmDestaque,
  gruposDoPainel,
  reduzirMovimento,
  onSelecionarTerritorio,
  onSelecionarGrupo,
  onLimparSelecao,
  camera,
}: MapaProps) {
  const container = useRef<HTMLDivElement>(null);
  // O mapa só entra aqui depois de carregado: é a partir daí que há o que desenhar
  const [mapa, setMapa] = useState<MapaDoMapLibre | null>(null);
  // Só importa se o zoom passou do limite dos ícones: guardar o zoom inteiro renderizaria a cada quadro
  const [zoomAlto, setZoomAlto] = useState(false);
  const geometria = useGeometria();

  // Os eventos do mapa nascem uma vez; este par entrega a eles sempre as funções mais recentes
  const aoSelecionar = useRef(onSelecionarTerritorio);
  const aoLimpar = useRef(onLimparSelecao);
  useEffect(() => {
    aoSelecionar.current = onSelecionarTerritorio;
    aoLimpar.current = onLimparSelecao;
  });
  const ultimaCamera = useRef(camera);

  // O mapa nasce uma vez
  useEffect(() => {
    const elemento = container.current;
    if (elemento === null) return;
    const novo = new MapaDoMapLibre({
      container: elemento,
      style: ESTILO,
      attributionControl: false,
      ...visaoDoMundo(),
    });
    novo.on("style.load", () => novo.setProjection({ type: "globe" }));
    novo.on("load", () => setMapa(novo));
    novo.on("zoom", () => setZoomAlto(novo.getZoom() >= ZOOM_DOS_MARCADORES));
    novo.on("click", (evento) => {
      // O clique num ícone é do ícone, não do país que está embaixo dele
      const alvo = evento.originalEvent.target;
      if (alvo instanceof Element && alvo.closest(".marcador-raiz") !== null) return;
      const feicao = novo.queryRenderedFeatures(evento.point, { layers: ["paises"] })[0];
      if (feicao === undefined) return aoLimpar.current(); // oceano
      const { codigo, tipo } = feicao.properties;
      if (tipo === "neutro" || typeof codigo !== "string") return; // área neutra: sem painel
      aoSelecionar.current(codigo);
    });
    novo.on("mousemove", "paises", (evento) => {
      const neutro = evento.features?.[0]?.properties["tipo"] === "neutro";
      novo.getCanvas().style.cursor = neutro ? "" : "pointer";
    });
    novo.on("mouseleave", "paises", () => {
      novo.getCanvas().style.cursor = "";
    });
    novo.addControl(new NavigationControl({ showCompass: false }), "bottom-right");
    novo.addControl(
      new AttributionControl({
        compact: true,
        customAttribution: "Fronteiras: Natural Earth (visão do Brasil)",
      }),
      "bottom-left",
    );
    return () => {
      setMapa(null);
      novo.remove();
    };
  }, []);

  // Cores e bordas: sempre a geometria mais os níveis atuais
  useEffect(() => {
    if (mapa === null || geometria.situacao !== "pronto") return;
    const fonte = mapa.getSource<GeoJSONSource>("paises");
    const dados = montarFeicoes(geometria.geometria, territorios);
    fonte?.setData(dados as unknown as Parameters<GeoJSONSource["setData"]>[0]);
  }, [mapa, geometria, territorios]);

  // Contorno da seleção. Kosovo e Malvinas contornam o grupo do soberano (propriedade `zoom`).
  useEffect(() => {
    if (mapa === null) return;
    const feicao =
      selecionado !== null && geometria.situacao === "pronto"
        ? geometria.geometria.features.find((f) => f.properties.codigo === selecionado)
        : undefined;
    mapa.setFilter("selecao", filtroDaSelecao(feicao?.properties.zoom ?? selecionado));
  }, [mapa, geometria, selecionado]);

  // Linha tracejada do país sem posto selecionado até o posto responsável
  useEffect(() => {
    if (mapa === null) return;
    const linha = linhaAteOResponsavel(selecionado, paisesSemPosto);
    const dados = {
      type: "FeatureCollection" as const,
      features:
        linha === null
          ? []
          : [
              {
                type: "Feature" as const,
                properties: {},
                geometry: { type: "LineString" as const, coordinates: linha },
              },
            ],
    };
    mapa.getSource<GeoJSONSource>("linha")?.setData(dados);
  }, [mapa, selecionado, paisesSemPosto]);

  // Pedidos de câmera: o plano é decidido por função pura; aqui só se executa
  useEffect(() => {
    if (mapa === null || ultimaCamera.current === camera) return;
    ultimaCamera.current = camera;
    const duration = duracaoDoMovimento(reduzirMovimento);
    // O ponto só é medido para "garantir-visivel"; os outros pedidos não consultam o mapa
    const alvo =
      camera.tipo === "garantir-visivel"
        ? { longitude: camera.longitude, latitude: camera.latitude }
        : { longitude: 0, latitude: 0 };
    const plano = planejarCamera(camera, () => medirMapa(mapa, alvo.longitude, alvo.latitude));
    switch (plano.tipo) {
      case "nenhum":
        break;
      case "mundo":
        mapa.easeTo({ ...visaoDoMundo(), bearing: 0, pitch: 0, duration });
        break;
      case "enquadrar": {
        const [[oeste, sul], [leste, norte]] = plano.caixa;
        mapa.fitBounds(
          [
            [oeste, sul],
            [leste, norte],
          ],
          {
            padding: {
              top: plano.margem.topo,
              left: plano.margem.esquerda,
              right: plano.margem.direita,
              bottom: plano.margem.baixo,
            },
            maxZoom: plano.zoomMaximo,
            duration,
          },
        );
        break;
      }
      case "centralizar":
        // Sem `zoom`: o mapa só anda até o ícone aparecer (FR-018c, FR-018h)
        mapa.easeTo({
          center: [plano.longitude, plano.latitude],
          offset: deslocamentoDaAreaLivre(plano.margem),
          duration,
        });
        break;
    }
  }, [mapa, camera, reduzirMovimento]);

  const zoom = zoomAlto ? ZOOM_DOS_MARCADORES : 0;
  const postosNoMapa = useMemo(
    () =>
      postosVisiveis(
        { zoom, selecionado, gruposDoPainel, grupoEmDestaque },
        postos,
        paisesSemPosto,
      ),
    [zoom, selecionado, gruposDoPainel, grupoEmDestaque, postos, paisesSemPosto],
  );
  const paisesSemPostoNoMapa = useMemo(
    () =>
      paisesSemPostoVisiveis(
        { zoom, selecionado, gruposDoPainel, grupoEmDestaque },
        paisesSemPosto,
      ),
    [zoom, selecionado, gruposDoPainel, grupoEmDestaque, paisesSemPosto],
  );

  return (
    <>
      {/*
        O maplibre-gl.css (fora de qualquer @layer) põe `position: relative` em `.maplibregl-map`
        e vence as classes do Tailwind. Por isso o posicionamento fica neste invólucro e o
        contêiner do mapa só ocupa 100% dele.
      */}
      <div
        role="img"
        aria-label="Mapa-múndi em globo, com a cor do nível de alerta de cada país"
        className="absolute inset-0"
      >
        <div ref={container} className="h-full w-full" />
      </div>

      {mapa !== null &&
        postosNoMapa.map((posto) => (
          <MarcadorNoMapa
            key={posto.grupo}
            mapa={mapa}
            longitude={posto.longitude}
            latitude={posto.latitude}
          >
            <Marcador
              variante={varianteDoMarcador(posto.tipos)}
              selo={seloDoMarcador(posto.tipos)}
              rotulo={rotuloDoGrupo(posto)}
              emDestaque={posto.grupo === grupoEmDestaque}
              reduzirMovimento={reduzirMovimento}
              onToque={() => onSelecionarGrupo(posto.grupo)}
            />
          </MarcadorNoMapa>
        ))}
      {mapa !== null &&
        paisesSemPostoNoMapa.map((pais) => (
          <MarcadorNoMapa
            key={pais.territorio}
            mapa={mapa}
            longitude={pais.longitude}
            latitude={pais.latitude}
          >
            <Marcador
              variante="sem-posto"
              selo={0}
              rotulo={rotuloDoPaisSemPosto(pais)}
              emDestaque={false}
              reduzirMovimento={reduzirMovimento}
              onToque={() => onSelecionarTerritorio(pais.territorio)}
            />
          </MarcadorNoMapa>
        ))}

      {geometria.situacao === "erro" && (
        <p
          role="alert"
          className="absolute left-1/2 top-1/2 z-10 -translate-x-1/2 rounded-lg bg-white px-4 py-2 text-sm shadow"
        >
          Não foi possível carregar o desenho do mapa. Recarregue a página.
        </p>
      )}
    </>
  );
}
