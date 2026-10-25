"""O OpenAPI exportado serve de fonte para os tipos do frontend."""

from pathlib import Path

from farol.api.exportar_openapi import gerar_openapi, main


def test_openapi_exportado_tem_as_rotas_e_o_prefixo() -> None:
    documento = gerar_openapi()
    assert documento["info"]["title"] == "Farol Atlas API"
    assert "/api/v1/saude" in documento["paths"]


def test_main_grava_o_arquivo(tmp_path: Path) -> None:
    destino = tmp_path / "openapi.json"
    assert main([str(destino)]) == 0
    assert '"/api/v1/saude"' in destino.read_text(encoding="utf-8")
