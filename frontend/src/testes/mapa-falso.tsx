/**
 * Mapa falso para os testes: o MapLibre precisa de WebGL, que não existe no jsdom.
 * Implementa `MapaProps` e expõe botões para simular os toques do usuário.
 */
import type { MapaProps } from "../funcionalidades/mapa/tipos";

export function MapaFalso(props: MapaProps) {
  return (
    <div data-testid="mapa-falso">
      <p data-testid="mapa-selecionado">{props.selecionado ?? ""}</p>
      <p data-testid="mapa-grupo-em-destaque">{props.grupoEmDestaque ?? ""}</p>
      <p data-testid="mapa-camera">{props.camera.tipo}</p>
      <p data-testid="mapa-reduzir-movimento">{String(props.reduzirMovimento)}</p>

      <ul aria-label="territórios desenhados">
        {props.territorios.map((t) => (
          <li
            key={t.codigo}
            data-codigo={t.codigo}
            data-nivel={t.nivel}
            data-borda-regional={t.bordaRegional ?? ""}
            data-esmaecido={String(t.esmaecido)}
          >
            <button type="button" onClick={() => props.onSelecionarTerritorio(t.codigo)}>
              {`tocar ${t.codigo}`}
            </button>
          </li>
        ))}
      </ul>

      <ul aria-label="ícones de postos">
        {props.postos.map((p) => (
          <li key={p.grupo} data-grupo={p.grupo} data-tipos={p.tipos.join("|")}>
            <button type="button" onClick={() => props.onSelecionarGrupo(p.grupo)}>
              {`tocar ícone ${p.grupo}`}
            </button>
          </li>
        ))}
      </ul>

      <button type="button" onClick={() => props.onLimparSelecao()}>
        tocar no oceano
      </button>
    </div>
  );
}
