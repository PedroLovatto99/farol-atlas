"""
Teste de coleta do Portal Consular (gov.br/mre)

Responde duas perguntas antes de construir o worker:

  1. ACESSO: um script consegue baixar as páginas ou cai na verificação humana?
  2. EXTRAÇÃO: dá para tirar título, data e texto dos alertas com segurança?

Como rodar:
    pip install requests beautifulsoup4 protego
    python testar_coleta.py

Rode primeiro na sua máquina. Depois rode de novo no servidor onde o worker vai
ficar hospedado: o resultado pode ser diferente (servidores na nuvem costumam
cair na verificação humana com mais facilidade).

O script faz menos de 10 requisições, com 2 segundos de pausa entre elas,
respeita o robots.txt e se identifica honestamente. Se cair na verificação,
ele para: não tente contornar.
"""

import json
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from protego import Protego

# ----------------------------------------------------------------------------- Configuração

CONTATO = "https://github.com/PedroLovatto99" # troque por um contato seu: é a forma educada de se identificar
USER_AGENT = f"MapaAlertasBR/0.1 (projeto pessoal de estudo; contato: {CONTATO})"
PAUSA_SEGUNDOS = 2.0
MAX_ALERTAS_ABERTOS = 3

ROBOTS = "https://www.gov.br/robots.txt"
LISTA_ALERTAS = "https://www.gov.br/mre/pt-br/assuntos/portal-consular/alertas%20e%20noticias/alertas"
REPARTICOES = "https://www.gov.br/mre/pt-br/assuntos/portal-consular/reparticoes-consulares-do-brasil"
PAGINAS_DE_POSTOS = [
    "https://www.gov.br/mre/pt-br/embaixada-ama",
    "https://www.gov.br/mre/pt-br/consulado-milao",
]

# Frases que aparecem na página de verificação humana do gov.br
SINAIS_DE_VERIFICACAO = ["testing whether you are a human", "prevent automated spam", "captcha"]

PASTA_AMOSTRAS = Path("amostras_coleta")


# ----------------------------------------------------------------------------- Acesso

def nova_sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})
    return sessao


def parece_verificacao(html: str) -> bool:
    texto = html.lower()
    return any(sinal in texto for sinal in SINAIS_DE_VERIFICACAO)


def baixar(sessao: requests.Session, url: str, robots: Protego | None) -> dict:
    """Baixa uma página e diz se veio o conteúdo de verdade ou um bloqueio."""
    resultado = {"url": url, "status": None, "ok": False, "motivo": "", "tamanho": 0, "segundos": 0.0, "html": ""}

    if robots is not None and not robots.can_fetch(url, USER_AGENT):
        resultado["motivo"] = "proibida pelo robots.txt"
        return resultado

    inicio = time.monotonic()
    try:
        resposta = sessao.get(url, timeout=30)
    except requests.RequestException as erro:
        resultado["motivo"] = f"erro de conexão: {erro.__class__.__name__}"
        return resultado
    finally:
        time.sleep(PAUSA_SEGUNDOS)

    resposta.encoding = resposta.encoding or "utf-8"
    html = resposta.text
    resultado.update(status=resposta.status_code, tamanho=len(html), html=html,
                     segundos=round(time.monotonic() - inicio, 2))

    if resposta.status_code in (403, 429):
        resultado["motivo"] = f"bloqueado (HTTP {resposta.status_code})"
    elif parece_verificacao(html):
        resultado["motivo"] = "caiu na verificação humana"
    elif resposta.status_code != 200:
        resultado["motivo"] = f"HTTP {resposta.status_code}"
    else:
        resultado["ok"] = True
        resultado["motivo"] = "conteúdo real"
    return resultado


# ----------------------------------------------------------------------------- Extração

def extrair_lista_de_alertas(html: str, url_da_pagina: str) -> list[dict]:
    """Lê a página de listagem: cada alerta é um bloco .conteudo com título, link e data."""
    soup = BeautifulSoup(html, "html.parser")
    blocos = soup.select(".listagem-noticias-com-foto .conteudo") or soup.select("#content-core .conteudo")
    alertas = []
    for bloco in blocos:
        link = bloco.select_one("h2.titulo a")
        data = bloco.select_one("span.data")
        if not link:
            continue
        alertas.append({
            "titulo": link.get_text(strip=True),
            "link": urljoin(url_da_pagina, link["href"]),
            "data": data.get_text(strip=True) if data else None,
        })
    return alertas


def extrair_alerta(html: str) -> dict:
    """Lê a página de um alerta: título, datas (do JSON-LD, mais confiável), categoria e texto."""
    soup = BeautifulSoup(html, "html.parser")

    publicado = modificado = None
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            dados = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and dados.get("@type") in ("NewsArticle", "Article"):
            publicado, modificado = dados.get("datePublished"), dados.get("dateModified")
            break
    if not publicado:  # reserva: o texto "Publicado em 10/07/2026 16h35"
        valor = soup.select_one("#plone-document-byline .documentPublished .value")
        publicado = valor.get_text(strip=True) if valor else None

    titulo = soup.select_one("h1.documentFirstHeading")
    corpo = soup.select_one('#content-core [property="rnews:articleBody"]') or soup.select_one("#content-core")
    categoria = soup.select_one("#form-widgets-categoria")
    texto = " ".join(corpo.get_text(" ", strip=True).split()) if corpo else ""

    return {
        "titulo": titulo.get_text(strip=True) if titulo else None,
        "publicado": publicado,
        "modificado": modificado,
        "categoria": categoria.get_text(strip=True) if categoria else None,
        "texto": texto,
    }


def contar_reparticoes(html: str) -> int:
    """Conta as linhas da tabela de repartições (países e postos que os atendem)."""
    soup = BeautifulSoup(html, "html.parser")
    tabela = soup.select_one("#content-core table") or soup.select_one("table")
    return max(len(tabela.select("tr")) - 1, 0) if tabela else 0


# ----------------------------------------------------------------------------- Execução

def mostrar(resultado: dict) -> None:
    sinal = "OK " if resultado["ok"] else "XX "
    status = resultado["status"] if resultado["status"] is not None else "-"
    print(f"  {sinal} [{status}] {resultado['motivo']:<30} {resultado['tamanho']:>8} caracteres  "
          f"{resultado['segundos']:>5}s  {resultado['url']}")


def salvar_amostra(nome: str, html: str) -> None:
    PASTA_AMOSTRAS.mkdir(exist_ok=True)
    (PASTA_AMOSTRAS / f"{nome}.html").write_text(html, encoding="utf-8")


def main() -> int:
    if "exemplo.com" in CONTATO:
        print("Aviso: troque CONTATO no topo do arquivo por um contato seu antes de rodar no servidor.\n")

    sessao = nova_sessao()
    resumo = {"acesso": [], "alertas_na_lista": 0, "alertas_lidos": [], "reparticoes": 0}

    # 1) robots.txt
    print("1. robots.txt")
    r = baixar(sessao, ROBOTS, robots=None)
    mostrar(r)
    if not r["ok"] or "user-agent" not in r["html"].lower():
        print("\nNão deu para ler o robots.txt de verdade. Parando aqui.")
        return 1
    robots = Protego.parse(r["html"])

    # 2) Acesso às páginas principais
    print("\n2. Acesso às páginas")
    paginas = {"lista_alertas": LISTA_ALERTAS, "reparticoes": REPARTICOES}
    paginas.update({f"posto_{i}": url for i, url in enumerate(PAGINAS_DE_POSTOS, 1)})
    baixadas = {}
    for nome, url in paginas.items():
        r = baixar(sessao, url, robots)
        mostrar(r)
        resumo["acesso"].append({k: r[k] for k in ("url", "status", "ok", "motivo")})
        if r["html"]:
            salvar_amostra(nome, r["html"])
        baixadas[nome] = r
        if r["motivo"] == "caiu na verificação humana" or r["motivo"].startswith("bloqueado"):
            print("\nO site bloqueou ou pediu verificação humana. Parando para não insistir.")
            break

    # 3) Extração
    print("\n3. Extração")
    lista = baixadas.get("lista_alertas")
    if lista and lista["ok"]:
        alertas = extrair_lista_de_alertas(lista["html"], LISTA_ALERTAS)
        resumo["alertas_na_lista"] = len(alertas)
        print(f"  Alertas na página de listagem: {len(alertas)}")
        for alerta in alertas[:5]:
            print(f"    {alerta['data'] or '??/??/????'}  {alerta['titulo']}")

        for numero, alerta in enumerate(alertas[:MAX_ALERTAS_ABERTOS], 1):
            r = baixar(sessao, alerta["link"], robots)
            if not r["ok"]:
                mostrar(r)
                break
            salvar_amostra(f"alerta_{numero}", r["html"])  # vira fixture dos testes da coleta
            dados = extrair_alerta(r["html"])
            resumo["alertas_lidos"].append({**dados, "link": alerta["link"], "texto": dados["texto"][:500]})
            print(f"\n  > {dados['titulo']}")
            print(f"    publicado: {dados['publicado']}  |  categoria: {dados['categoria']}")
            print(f"    texto ({len(dados['texto'])} caracteres): {dados['texto'][:160]}...")

    rep = baixadas.get("reparticoes")
    if rep and rep["ok"]:
        resumo["reparticoes"] = contar_reparticoes(rep["html"])
        print(f"\n  Linhas na tabela de repartições: {resumo['reparticoes']} (esperado: cerca de 197)")

    # 4) Resultado
    Path("resultado_coleta.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    tudo_ok = all(item["ok"] for item in resumo["acesso"]) and resumo["alertas_na_lista"] > 0
    print("\n" + ("Tudo certo: acesso e extração funcionaram." if tudo_ok
                  else "Algo falhou. Veja os XX acima e as páginas salvas em amostras_coleta/."))
    print("Resumo salvo em resultado_coleta.json")
    return 0 if tudo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
