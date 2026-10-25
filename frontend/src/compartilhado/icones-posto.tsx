import {
  IconBriefcase,
  IconBuilding,
  IconBuildingBank,
  IconMapPinShare,
} from "@tabler/icons-react";

export type VarianteDoIcone = "embaixada" | "consulado" | "escritorio" | "sem-posto";

interface Props {
  variante: VarianteDoIcone;
  size?: number;
}

/** Um ícone por tipo de posto, o mesmo no mapa e no painel: embaixada, consulado, escritório. */
export function IconeDoPosto({ variante, size = 18 }: Props) {
  switch (variante) {
    case "embaixada":
      return <IconBuildingBank aria-hidden size={size} />;
    case "consulado":
      return <IconBuilding aria-hidden size={size} />;
    case "escritorio":
      return <IconBriefcase aria-hidden size={size} />;
    case "sem-posto":
      return <IconMapPinShare aria-hidden size={size} />;
  }
}
