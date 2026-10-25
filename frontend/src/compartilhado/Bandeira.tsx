import "flag-icons/css/flag-icons.min.css";

/** Código de bandeira do flag-icons: dois caracteres (ex.: "dk") ou o formato "gb-eng". */
const CODIGO_VALIDO = /^[a-z]{2}(?:-[a-z]{3})?$/;

interface Props {
  /** Código já resolvido pelo backend (`bandeira`). Nulo para Taiwan: não mostra nada. */
  codigo: string | null;
}

/**
 * Bandeira em SVG (flag-icons), nunca emoji. O código chega pronto do backend: Kosovo e Malvinas
 * trazem o da Sérvia e o da Argentina, e este componente nunca monta bandeira a partir de XK ou FK.
 * Decorativa: o nome do país ao lado já diz tudo.
 */
export function Bandeira({ codigo }: Props) {
  if (codigo === null) return null;
  const minusculo = codigo.toLowerCase();
  if (!CODIGO_VALIDO.test(minusculo)) return null;
  return <span aria-hidden="true" className={`fi fi-${minusculo} shrink-0 rounded-sm`} />;
}
