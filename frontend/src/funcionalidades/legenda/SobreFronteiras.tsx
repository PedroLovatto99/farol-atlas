import { useState } from "react";
import { Modal } from "../../compartilhado/Modal";

const TITULO = "Sobre as fronteiras deste mapa";

/** Link ao lado da legenda; a explicação curta abre num modal (FR-036). */
export function SobreFronteiras() {
  const [aberto, setAberto] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setAberto(true)}
        className="min-h-11 text-left text-sm text-marinho underline underline-offset-2"
      >
        {TITULO}
      </button>
      <Modal aberto={aberto} titulo={TITULO} onFechar={() => setAberto(false)}>
        <p>
          O mapa segue a posição oficial do Brasil. Os desenhos vêm do Natural Earth, na versão que
          representa as fronteiras como o Brasil as reconhece.
        </p>
        <h3 className="font-semibold">Casos especiais</h3>
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong>Kosovo</strong>: o Brasil não reconhece a independência. O mapa o mostra como
            parte da Sérvia.
          </li>
          <li>
            <strong>Taiwan</strong> aparece como parte da China, sem bandeira, seguindo a posição do
            Brasil.
          </li>
          <li>
            <strong>Malvinas</strong>: são administradas pelo Reino Unido. O Brasil apoia os
            direitos da Argentina sobre elas e defende a negociação entre os dois países; o mapa as
            mostra como parte da Argentina.
          </li>
          <li>
            <strong>Saara Ocidental</strong> e <strong>Antártida</strong> são áreas sem soberania
            reconhecida: aparecem em cor neutra, sem nível de alerta e sem painel.
          </li>
          <li>
            <strong>Dependências</strong> (como Groenlândia, Guiana Francesa e Porto Rico) seguem o
            país soberano: valem o alerta mais recente entre o do próprio território e o do
            soberano.
          </li>
        </ul>
      </Modal>
    </>
  );
}
