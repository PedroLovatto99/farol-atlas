import { IconeDoPosto } from "../../compartilhado/icones-posto";
import type { VarianteDoMarcador } from "./marcadores";

interface Props {
  variante: VarianteDoMarcador;
  /** Quantos postos além do principal dividem o ícone: o selo "+1" (FR-018d). */
  selo: number;
  /** Nome acessível do ícone, ex.: "Embaixada em Washington". */
  rotulo: string;
  /** FR-018a: maior, com contorno e à frente; o tamanho e o contorno vêm dos tokens de tema.css. */
  emDestaque: boolean;
  /** FR-018f: o destaque aparece sem animação. */
  reduzirMovimento: boolean;
  onToque(): void;
}

/**
 * Ícone de posto no mapa. É um botão, para teclado e leitor de tela. O destaque é um estado
 * acessível (`aria-current`, `data-em-destaque`), nunca só uma cor; as medidas ficam no CSS.
 */
export function Marcador({ variante, selo, rotulo, emDestaque, reduzirMovimento, onToque }: Props) {
  return (
    <button
      type="button"
      aria-label={rotulo}
      aria-current={emDestaque ? "true" : undefined}
      data-marcador=""
      data-variante={variante}
      data-em-destaque={String(emDestaque)}
      data-animar={String(emDestaque && !reduzirMovimento)}
      className="marcador"
      onClick={(evento) => {
        // O clique é do ícone, não do mapa embaixo dele
        evento.stopPropagation();
        onToque();
      }}
    >
      <IconeDoPosto variante={variante} size={18} />
      {selo > 0 && (
        <span aria-hidden="true" className="marcador-selo">
          +{selo}
        </span>
      )}
    </button>
  );
}
