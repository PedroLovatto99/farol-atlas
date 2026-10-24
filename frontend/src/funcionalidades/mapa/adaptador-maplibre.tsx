/**
 * Adaptador do MapLibre GL JS 6: o ÚNICO arquivo que importa `maplibre-gl` (princípio III).
 * Cumpre `MapaProps`; trocar a biblioteca só mexe aqui.
 *
 * Nesta etapa (história P1) o mapa é um globo 3D só com oceano e países: preenchimento pela cor
 * do nível, fronteiras e a borda de destaque das regiões mais graves. Seleção, câmera e ícones
 * de postos chegam nas histórias P2 e P3.
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
import { montarFeicoes } from "./feicoes";
import type { MapaProps } from "./tipos";
import { useGeometria } from "./useGeometria";

// O MapLibre 6 lê os mapas num web worker. O Vite (no modo de desenvolvimento) pré-empacota a
// biblioteca e o endereço do worker se perde ("Worker failed to load"): informá-lo aqui funciona
// no desenvolvimento e no build.
setWorkerUrl(urlDoWorker);

const COR_DO_OCEANO = "#DCE8F2";
const LARGURA_MAXIMA_DO_CELULAR = 700;
const COLECAO_VAZIA = { type: "FeatureCollection" as const, features: [] };

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
  ],
};

function visaoDoMundo(): { center: [number, number]; zoom: number } {
  const celular = window.innerWidth <= LARGURA_MAXIMA_DO_CELULAR;
  return { center: [25, 18], zoom: celular ? 0.85 : 1.75 };
}

export function MapaMapLibre({ territorios }: MapaProps) {
  const container = useRef<HTMLDivElement>(null);
  const mapaRef = useRef<MapaDoMapLibre | null>(null);
  const [carregado, setCarregado] = useState(false);
  const geometria = useGeometria();

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
