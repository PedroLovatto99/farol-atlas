import { useEffect, useState } from "react";
import { QUANTIDADE_DE_ESTRELAS, SEMENTE_DO_CEU, TAMANHO_DO_CEU, gerarEstrelas } from "./estrelas";

/** `undefined`: ainda não tentou; `null`: sem canvas (o fundo fica só escuro). */
let imagemDoCeu: string | null | undefined;

/** Só para os testes: esquece o céu já desenhado. */
export function limparCacheDoCeu(): void {
  imagemDoCeu = undefined;
}

/** Desenha o quadro de estrelas uma única vez por carga da página e devolve a imagem. */
function desenharCeu(): string | null {
  const canvas = document.createElement("canvas");
  canvas.width = TAMANHO_DO_CEU;
  canvas.height = TAMANHO_DO_CEU;
  const contexto = canvas.getContext("2d");
  if (contexto === null) return null;
  for (const estrela of gerarEstrelas(SEMENTE_DO_CEU, QUANTIDADE_DE_ESTRELAS, TAMANHO_DO_CEU)) {
    const [r, g, b] = estrela.cor;
    if (estrela.brilhante) {
      // halo discreto: um degradê que some em quatro raios (sem outro arco, para ser barato)
      const alcance = estrela.raio * 4;
      const halo = contexto.createRadialGradient(
        estrela.x,
        estrela.y,
        0,
        estrela.x,
        estrela.y,
        alcance,
      );
      halo.addColorStop(0, `rgba(${r},${g},${b},0.18)`);
      halo.addColorStop(1, `rgba(${r},${g},${b},0)`);
      contexto.fillStyle = halo;
      contexto.fillRect(estrela.x - alcance, estrela.y - alcance, alcance * 2, alcance * 2);
    }
    contexto.beginPath();
    contexto.arc(estrela.x, estrela.y, estrela.raio, 0, Math.PI * 2);
    contexto.fillStyle = `rgba(${r},${g},${b},${estrela.opacidade})`;
    contexto.fill();
  }
  return canvas.toDataURL("image/png");
}

/**
 * O céu atrás do globo: quase preto, com estrelas. O MapLibre deixa o canvas transparente fora da
 * esfera, então basta este fundo por baixo do mapa. É uma imagem gerada uma vez (semente fixa) e
 * repetida pelo CSS: nada é recalculado quando o mapa se mexe, e não há animação (nem brilho
 * piscando), então "reduzir movimento" não tem o que desligar.
 */
export function CeuEstrelado() {
  const [imagem, setImagem] = useState<string | null>(imagemDoCeu ?? null);

  useEffect(() => {
    if (imagem !== null || imagemDoCeu === null) return;
    // depois da primeira pintura: desenhar o quadro não atrasa a abertura do site
    const espera = window.setTimeout(() => {
      imagemDoCeu ??= desenharCeu();
      setImagem(imagemDoCeu);
    }, 0);
    return () => window.clearTimeout(espera);
  }, [imagem]);

  return (
    <div
      data-testid="ceu-estrelado"
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 bg-ceu"
      style={
        imagem === null
          ? undefined
          : {
              backgroundImage: `url(${imagem})`,
              backgroundRepeat: "repeat",
              backgroundSize: `${TAMANHO_DO_CEU}px ${TAMANHO_DO_CEU}px`,
            }
      }
    />
  );
}
