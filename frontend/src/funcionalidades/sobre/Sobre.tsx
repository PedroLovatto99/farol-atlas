import { useState } from "react";
import { Modal } from "../../compartilhado/Modal";
import { URL_DO_PORTAL_CONSULAR } from "../aviso/Aviso";

const LINK = "font-semibold text-marinho underline underline-offset-2";

/** Link "Sobre": o que é o site, que não é oficial e de onde vêm os dados. */
export function Sobre() {
  const [aberto, setAberto] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setAberto(true)}
        className="min-h-11 rounded-lg bg-white/90 px-3 text-sm text-marinho underline underline-offset-2 shadow-sm"
      >
        Sobre
      </button>
      <Modal aberto={aberto} titulo="Sobre o Farol Atlas" onFechar={() => setAberto(false)}>
        <p>
          O Farol Atlas mostra, num mapa, o nível de alerta de viagem que o Itamaraty publica para
          cada país. É um projeto pessoal e <strong>não é um serviço oficial</strong>: confirme
          sempre no{" "}
          <a
            href={URL_DO_PORTAL_CONSULAR}
            target="_blank"
            rel="noopener noreferrer"
            className={LINK}
          >
            Portal Consular do Itamaraty
          </a>
          .
        </p>
        <p>
          Os níveis vêm dos alertas do Portal Consular, lidos uma vez por dia. Sem dado confirmado,
          o país aparece como “não verificado”.
        </p>
        <h3 className="font-semibold">Fontes</h3>
        <ul className="list-disc space-y-1 pl-5">
          <li>Alertas e lista de repartições: Itamaraty (Portal Consular).</li>
          <li>
            Fronteiras:{" "}
            <a
              href="https://www.naturalearthdata.com/"
              target="_blank"
              rel="noopener noreferrer"
              className={LINK}
            >
              Natural Earth
            </a>{" "}
            (domínio público).
          </li>
          <li>
            Lista de postos brasileiros:{" "}
            <a
              href="https://en.wikipedia.org/wiki/List_of_diplomatic_missions_of_Brazil"
              target="_blank"
              rel="noopener noreferrer"
              className={LINK}
            >
              Wikipédia
            </a>{" "}
            (CC BY-SA) e Itamaraty.
          </li>
        </ul>
      </Modal>
    </>
  );
}
