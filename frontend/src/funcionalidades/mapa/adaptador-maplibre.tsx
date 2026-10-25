/**
 * Adaptador do MapLibre GL JS 6: o ÚNICO arquivo que importa `maplibre-gl` (princípio III).
 * Cumpre `MapaProps`; trocar a biblioteca só mexe aqui.
 *
 * O mapa é um globo 3D só com oceano e países: preenchimento pela cor do nível, fronteiras, borda
 * de destaque das regiões mais graves e contorno do país selecionado. Toque em país seleciona;
 * oceano limpa a seleção; área neutra é ignorada (FR-016). Os pedidos de câmera são só executados
 * aqui: a regra de enquadramento é função pura (`enquadramento.ts`). Os ícones de postos chegam na
 * história P3.
 */
import "maplibre-gl/dist/maplibre-gl.css";
import {
  AttributionControl,
  Map as MapaDoMapLibre,
  NavigationControl,
  setWorkerUrl,
  type GeoJSONSource,
  type StyleSpecification,
} from "maplibre-gl";
import urlDoWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { useEffect, useRef, useState } from "react";
import { duracaoDoMovimento } from "./enquadramento";
import { montarFeicoes } from "./feicoes";
import type { MapaProps } from "./tipos";
import { useGeometria } from "./useGeometria";

// O MapLibre 6 lê os mapas num web worker. O Vite (no modo de desenvolvimento) pré-empacota a
// biblioteca e o endereço do worker se perde ("Worker failed to load"): informá-lo aqui funciona
// no desenvolvimento e no build.
setWorkerUrl(urlDoWorker);

const COR_DO_OCEANO = "#DCE8F2";
const COR_DA_SELECAO = "#0C447C";
const LARGURA_MAXIMA_DO_CELULAR = 700;
const COLECAO_VAZIA = { type: "FeatureCollection" as const, features: [] };

/** Desenha o contorno de todo o grupo de enquadramento; sem seleção, o filtro não casa com nada. */
function filtroDaSelecao(grupo: string | null): ["==", ["get", string], string] {
  return ["==", ["get", "zoom"], grupo ?? ""];
}

/** Só oceano e países, sem mapa de fundo. As cores vêm das propriedades de cada feição. */
const ESTILO: StyleSpecification = {
  version: 8,
  sources: { paises: { type: "geojson", data: COLECAO_VAZIA } },
  layers: [
    { id: "oceano", type: "background", paint: { "background-color": COR_DO_OCEANO } },
    { id: "paises", type: "fill", source: "paises", paint: { "fill-color": ["get", "cor"] } },
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
      paint: { "line-color": ["get", "borda_regional"], "line-width": 2.5 },
    },
    {
      // Contorno do país selecionado: o filtro (grupo `zoom`) é trocado em `filtroDaSelecao`
      id: "selecao",
      type: "line",
      source: "paises",
      filter: filtroDaSelecao(null),
      paint: { "line-color": COR_DA_SELECAO, "line-width": 3 },
    },
  ],
};

function visaoDoMundo(): { center: [number, number]; zoom: number } {
  const celular = window.innerWidth <= LARGURA_MAXIMA_DO_CELULAR;
  return { center: [25, 18], zoom: celular ? 0.85 : 1.75 };
}

export function MapaMapLibre({
  territorios,
  selecionado,
  reduzirMovimento,
  onSelecionarTerritorio,
  onLimparSelecao,
  camera,
}: MapaProps) {
  const container = useRef<HTMLDivElement>(null);
  const mapaRef = useRef<MapaDoMapLibre | null>(null);
  const [carregado, setCarregado] = useState(false);
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
    const mapa = new MapaDoMapLibre({
      container: elemento,
      style: ESTILO,
      attributionControl: false,
      ...visaoDoMundo(),
    });
    mapa.on("style.load", () => mapa.setProjection({ type: "globe" }));
    mapa.on("load", () => setCarregado(true));
    mapa.on("click", (evento) => {
      const feicao = mapa.queryRenderedFeatures(evento.point, { layers: ["paises"] })[0];
      if (feicao === undefined) return aoLimpar.current(); // oceano
      const { codigo, tipo } = feicao.properties;
      if (tipo === "neutro" || typeof codigo !== "string") return; // área neutra: sem painel
      aoSelecionar.current(codigo);
    });
    mapa.on("mousemove", "paises", (evento) => {
      const neutro = evento.features?.[0]?.properties["tipo"] === "neutro";
      mapa.getCanvas().style.cursor = neutro ? "" : "pointer";
    });
    mapa.on("mouseleave", "paises", () => {
      mapa.getCanvas().style.cursor = "";
    });
    mapa.addControl(new NavigationControl({ showCompass: false }), "bottom-right");
    mapa.addControl(
      new AttributionControl({
        compact: true,
        customAttribution: "Fronteiras: Natural Earth (visão do Brasil)",
      }),
      "bottom-left",
    );
    mapaRef.current = mapa;
    return () => {
      mapaRef.current = null;
      mapa.remove();
    };
  }, []);

  // Cores e bordas: sempre a geometria mais os níveis atuais
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!carregado || mapa === null || geometria.situacao !== "pronto") return;
    const fonte = mapa.getSource<GeoJSONSource>("paises");
    const dados = montarFeicoes(geometria.geometria, territorios);
    fonte?.setData(dados as unknown as Parameters<GeoJSONSource["setData"]>[0]);
  }, [carregado, geometria, territorios]);

  // Contorno da seleção. Kosovo e Malvinas contornam o grupo do soberano (propriedade `zoom`).
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!carregado || mapa === null) return;
    const feicao =
      selecionado !== null && geometria.situacao === "pronto"
        ? geometria.geometria.features.find((f) => f.properties.codigo === selecionado)
        : undefined;
    mapa.setFilter("selecao", filtroDaSelecao(feicao?.properties.zoom ?? selecionado));
  }, [carregado, geometria, selecionado]);

  // Pedidos de câmera: só executa; quem decide o enquadramento é a tela
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!carregado || mapa === null || ultimaCamera.current === camera) return;
    ultimaCamera.current = camera;
    const duration = duracaoDoMovimento(reduzirMovimento);
    switch (camera.tipo) {
      case "mundo":
        mapa.easeTo({ ...visaoDoMundo(), bearing: 0, pitch: 0, duration });
        break;
      case "enquadrar": {
        const [[oeste, sul], [leste, norte]] = camera.caixa;
        mapa.fitBounds(
          [
            [oeste, sul],
            [leste, norte],
          ],
          {
            padding: {
              top: camera.margem.topo,
              left: camera.margem.esquerda,
              right: camera.margem.direita,
              bottom: camera.margem.baixo,
            },
            maxZoom: camera.zoomMaximo,
            duration,
          },
        );
        break;
      }
      case "garantir-visivel": // chega com os ícones de postos (história P3)
      case "manter":
        break;
    }
  }, [carregado, camera, reduzirMovimento]);

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
