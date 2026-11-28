"""Informe en Markdown → HTML con formato para la slide «documento» del director.

Cubre lo que emite assessment/__main__.py: títulos # a ###, tablas con barras, listas «- »
(un nivel de anidación por cada dos espacios), párrafos, **negrita**, `código` y [enlaces](url).
El texto se escapa antes de dar formato. Un enlace queda como texto subrayado sin href, para
que un clic en la slide nunca saque a la consola de su página.
"""
from __future__ import annotations

import html
import re

_TITULO = re.compile(r"^(#{1,3}) (.+)$")
_LISTA = re.compile(r"^( *)- (.*)$")
_SEPARADOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")
_ENLACE = re.compile(r"\[([^\]]+)\]\([^)\s]+\)")
_NEGRITA = re.compile(r"\*\*(.+?)\*\*")


def _en_linea(texto: str) -> str:
    partes = html.escape(texto.strip(), quote=False).split("`")
    if len(partes) % 2 == 0:  # un acento grave sin pareja se queda como texto
        partes[-2:] = ["`".join(partes[-2:])]
    for i, parte in enumerate(partes):
        if i % 2:
            partes[i] = f"<code>{parte}</code>"
        else:
            partes[i] = _NEGRITA.sub(r"<strong>\1</strong>", _ENLACE.sub(r'<span class="enlace">\1</span>', parte))
    return "".join(partes)


def _celdas(linea: str) -> list[str]:
    linea = linea.strip()
    linea = linea[1:] if linea.startswith("|") else linea
    linea = linea[:-1] if linea.endswith("|") else linea
    return [celda.strip() for celda in linea.split("|")]


def _tabla(filas: list[str]) -> str:
    cabecera = "".join(f"<th>{_en_linea(c)}</th>" for c in _celdas(filas[0]))
    cuerpo = "".join("<tr>" + "".join(f"<td>{_en_linea(c)}</td>" for c in _celdas(f)) + "</tr>" for f in filas[2:])
    return f"<table><thead><tr>{cabecera}</tr></thead><tbody>{cuerpo}</tbody></table>"


def _lista(items: list[tuple[int, str]]) -> str:
    salida, nivel_abierto = [], -1
    for nivel, texto in items:
        nivel = min(nivel, nivel_abierto + 1)  # no se salta niveles
        if nivel > nivel_abierto:
            salida.append("<ul>")
            nivel_abierto = nivel
        else:
            salida.append("</li>")
            while nivel_abierto > nivel:
                salida.append("</ul></li>")
                nivel_abierto -= 1
        salida.append(f"<li>{_en_linea(texto)}")
    salida.append("</li>")
    salida.extend("</ul></li>" for _ in range(nivel_abierto))
    salida.append("</ul>")
    return "".join(salida)


def _es_tabla(lineas: list[str], i: int) -> bool:
    return lineas[i].lstrip().startswith("|") and i + 1 < len(lineas) and bool(_SEPARADOR.match(lineas[i + 1].strip()))


def _filtrar(md: str, secciones: list[str]) -> str:
    """Deja el título «# » del informe y solo las secciones «## » nombradas."""
    salida, dentro = [], None
    for linea in md.splitlines():
        if dentro is None and linea.startswith("# "):
            salida.append(linea)
            continue
        if linea.startswith("## "):
            dentro = linea[3:].strip() in secciones
        if dentro:
            salida.append(linea)
    return "\n".join(salida)


def a_html(md: str, secciones: list[str] | None = None) -> str:
    if secciones is not None:
        md = _filtrar(md, secciones)
    lineas = md.splitlines()
    bloques, i = [], 0
    while i < len(lineas):
        linea = lineas[i]
        if not linea.strip():
            i += 1
        elif titulo := _TITULO.match(linea):
            n = len(titulo.group(1))
            bloques.append(f"<h{n}>{_en_linea(titulo.group(2))}</h{n}>")
            i += 1
        elif _es_tabla(lineas, i):
            fin = i + 2
            while fin < len(lineas) and lineas[fin].lstrip().startswith("|"):
                fin += 1
            bloques.append(_tabla(lineas[i:fin]))
            i = fin
        elif _LISTA.match(linea):
            items = []
            while i < len(lineas) and (item := _LISTA.match(lineas[i])):
                items.append((len(item.group(1)) // 2, item.group(2)))
                i += 1
            bloques.append(_lista(items))
        else:
            parrafo = [linea.strip()]
            i += 1
            while i < len(lineas) and lineas[i].strip() and not (
                _TITULO.match(lineas[i]) or _LISTA.match(lineas[i]) or _es_tabla(lineas, i)
            ):
                parrafo.append(lineas[i].strip())
                i += 1
            bloques.append(f"<p>{_en_linea(' '.join(parrafo))}</p>")
    return "\n".join(bloques)
