"""Correlación de fuentes y política determinista para criterios de renovaciones (REN-001, REN-002 y backlog)."""
from collections import Counter
from dataclasses import dataclass
import re

from .evidence import CRITERION, SECONDARY_CRITERION, Evidence, Result

STRING = r'"(?:[^"\\\n]|\\.)*"'
TOKEN = re.compile(rf'{STRING}|//[^\n]*|/\*[^*]*(?:\*(?!/)[^*]*)*\*/')
HEADER = re.compile(r"[ \t\r\n]*using[ \t\r\n]+Xunit[ \t\r\n]*;[ \t\r\n]*public[ \t\r\n]+class[ \t\r\n]+(\w+)[ \t\r\n]*\{")
ATTR_BLOCK = r"(?:\[[ \t]*\w+(?:[ \t]*\([^()\n]*\))?[ \t]*\][ \t\r\n]*)+"
TEST = re.compile(
    rf"(?P<attrs>{ATTR_BLOCK})"
    r"public[ \t\r\n]+void[ \t\r\n]+(?P<name>\w+)[ \t]*\((?P<params>[^()]*)\)[ \t\r\n]*"
    r"\{(?P<body>[^{}]*)\}"
)
TRAIT_ANY = re.compile(r'\[[ \t]*Trait[ \t]*\([ \t]*"Criterio"[ \t]*,[ \t]*"(REN-\d+)"[ \t]*\)[ \t]*\]')
FACT = re.compile(r"\[[ \t]*Fact[ \t]*\]")
THEORY = re.compile(r"\[[ \t]*Theory[ \t]*\]")
INLINE_DAY = re.compile(r"\[[ \t]*InlineData[ \t]*\([ \t]*(\d+)[ \t]*\)[ \t]*\]")
FIXTURE = re.compile(
    r"static[ \t\r\n]+Datos[ \t\r\n]+Caso[ \t]*\([ \t]*bool[ \t\r\n]+cancelado[ \t]*,[ \t]*int[ \t\r\n]+dias[ \t]*\)[ \t]*=>[ \t]*new[ \t]*\("
    rf"[ \t\r\n]*\[[ \t\r\n]*new[ \t\r\n]+Contrato[ \t]*\([ \t]*Guid\.NewGuid\(\)[ \t]*,[ \t]*{STRING}[ \t]*,[ \t]*{STRING}[ \t]*,[ \t]*{STRING}"
    r"[ \t]*,[ \t]*Hoy\.AddDays\(dias\)[ \t]*,[ \t]*cancelado[ \t]*\)[ \t\r\n]*\][ \t]*,[ \t]*\[[ \t]*\][ \t]*\)[ \t]*;"
)
SCENARIO = re.compile(
    r"[ \t\r\n]*var[ \t\r\n]+(\w+)[ \t]*=[ \t]*Caso[ \t]*\([ \t]*true[ \t]*,[ \t]*(?:1|7|30)[ \t]*\)[ \t]*;"
    r"[ \t\r\n]*Renovaciones\.Evaluar[ \t]*\([ \t]*\1[ \t]*,[ \t]*Hoy[ \t]*\)[ \t]*;"
    r"[ \t\r\n]*(?P<assertion>Assert\.Empty)[ \t]*\([ \t]*\1[ \t]*\.[ \t]*Avisos[ \t]*\)[ \t]*;[ \t\r\n]*"
)
ACTIVE_SCENARIO = re.compile(
    r"[ \t\r\n]*var[ \t\r\n]+(\w+)[ \t]*=[ \t]*Caso[ \t]*\([ \t]*false[ \t]*,[ \t]*(\w+)[ \t]*\)[ \t]*;"
    r"[ \t\r\n]*Renovaciones\.Evaluar[ \t]*\([ \t]*\1[ \t]*,[ \t]*Hoy[ \t]*\)[ \t]*;"
    r"[ \t\r\n]*Renovaciones\.Evaluar[ \t]*\([ \t]*\1[ \t]*,[ \t]*Hoy[ \t]*\)[ \t]*;"
    r"[ \t\r\n]*Assert\.Single[ \t]*\([ \t]*\1[ \t]*\.[ \t]*Avisos[ \t]*\)[ \t]*;[ \t\r\n]*"
)
EMPTY_FAILURE = re.compile(r"^Assert\.Empty\(\) Failure: Collection was not empty\s+Collection: \[Aviso \{")


@dataclass(frozen=True)
class SourceTest:
    file: str
    line: int
    method: str
    linked: bool
    code: str
    fixture: str
    assertion_line: int | None
    traits: tuple[str, ...] = ()
    active_idempotent: bool = False
    inline_days: tuple[int, ...] = ()

    @property
    def ref(self) -> str:
        return f"{self.file}:{self.line}"

    def reference(self) -> dict:
        return {"id": self.ref, "archivo": self.file, "linea": self.line, "metodo": self.method,
                "vinculada": self.linked, "linea_asercion": self.assertion_line}


def source_tests(sources: dict[str, str]) -> list[SourceTest]:
    # shortcut: reconoce la forma de las pruebas de esta demo, ampliar con Roslyn para C# arbitrario.
    tests = []
    for path, source in sources.items():
        clean = TOKEN.sub(lambda m: re.sub(r"[^\n]", " ", m[0]) if m[0].startswith("/") else m[0], source)
        header = HEADER.match(clean)
        if not header:
            continue
        braces = re.compile(rf"{STRING}|[{{}}]")
        depth = 1
        end = len(clean)
        for token in braces.finditer(clean, header.end()):
            depth += (token[0] == "{") - (token[0] == "}")
            if depth == 0:
                end = token.start()
                break

        def direct_member(offset: int) -> bool:
            tokens = [m[0] for m in braces.finditer(clean, header.end(), offset)]
            return tokens.count("{") == tokens.count("}")

        has_directives = bool(re.search(r"^[ \t]*#", clean, re.M))
        fixture = next((m for m in FIXTURE.finditer(clean, header.end(), end) if direct_member(m.start())), None)
        for match in TEST.finditer(clean, header.end(), end):
            attrs = match["attrs"]
            if not direct_member(match.start()) or not re.search(r"\[[ \t]*(?:Fact|Theory)\b", attrs):
                continue
            traits = tuple(dict.fromkeys(TRAIT_ANY.findall(attrs)))
            linked = "REN-001" in traits
            scenario = SCENARIO.fullmatch(match["body"])
            assertion_line = None
            if linked and FACT.search(attrs) and not match["params"].strip() and fixture and scenario and not has_directives:
                assertion_line = clean.count("\n", 0, match.start("body") + scenario.start("assertion")) + 1

            inline_days = tuple(int(d) for d in INLINE_DAY.findall(attrs))
            param_match = re.fullmatch(r"[ \t]*int[ \t\r\n]+(\w+)[ \t]*", match["params"])
            active_match = ACTIVE_SCENARIO.fullmatch(match["body"])
            active_idempotent = bool(
                THEORY.search(attrs)
                and param_match
                and active_match
                and active_match[2] == param_match[1]
                and set(inline_days) >= {1, 7, 30}
                and fixture
                and not has_directives
            )
            tests.append(SourceTest(
                path,
                clean.count("\n", 0, match.start()) + 1,
                f"{header[1]}.{match['name']}",
                linked,
                source[match.start():match.end()],
                source[fixture.start():fixture.end()] if fixture else "",
                assertion_line,
                traits=traits,
                active_idempotent=active_idempotent,
                inline_days=inline_days,
            ))
    return tests


def is_criterion_failure(row: Result, test: SourceTest, evidence: Evidence) -> bool:
    if not EMPTY_FAILURE.match(row.error):
        return False
    frame = re.compile(rf"^[ \t]*at {re.escape(test.method)}\(\) in (.+):line (\d+)[ \t]*$")
    return any((match := frame.fullmatch(line))
               and match[1] == str(evidence.root / test.file) and int(match[2]) == test.assertion_line
               for line in row.stack.splitlines())


def validate_references(references: list[dict], tests: list[SourceTest], results: list[Result]) -> list[dict]:
    tests_by_ref = {test.ref: test for test in tests}
    results_by_id = {row.execution_id: row for row in results}
    counts = Counter(test.method for test in tests)
    checks = []
    for ref in references:
        test = tests_by_ref.get(ref["prueba"])
        rows = [results_by_id.get(item) for item in ref["ejecuciones"]]
        source_valid = bool(test and counts[test.method] == 1)
        valid = source_valid and bool(rows) and all(row and row.method == test.method for row in rows)
        checks.append({**ref, "fuente_valida": source_valid, "correlacion_valida": valid,
                       "cubre_criterio": valid and test.assertion_line is not None})
    return checks


def evaluate(evidence: Evidence, tests: list[SourceTest]) -> dict:
    verdict = "EVIDENCIA_INSUFICIENTE"
    linked = [test for test in tests if test.linked]
    reasons, support, outcomes = [], [], set()
    counts = Counter(test.method for test in tests)
    for test in linked:
        rows = [row for row in evidence.results if row.method == test.method]
        support.append({**test.reference(), "resultados": [row.execution_id for row in rows]})
        if counts[test.method] != 1 or len(rows) > 1:
            reasons.append(f"La correlación de {test.method} es ambigua.")
        elif not rows:
            reasons.append(f"El TRX no contiene una ejecución de {test.method}.")
        elif rows[0].outcome in {"NotExecuted", "Skipped"}:
            reasons.append(f"Se omitió {test.method}.")
        elif test.assertion_line is None:
            reasons.append(f"La fuente de {test.method} no permite confirmar el escenario de cancelación.")
        elif rows[0].outcome == "Passed":
            outcomes.add("VERIFICADO")
            reasons.append(f"{test.method} evaluó un contrato cancelado y comprobó que la bandeja seguía vacía.")
        elif rows[0].outcome == "Failed" and is_criterion_failure(rows[0], test, evidence):
            outcomes.add("INCUMPLIDO")
            reasons.append(f"{test.method} falló en Assert.Empty(datos.Avisos). El TRX registra un aviso generado.")
        else:
            reasons.append(f"{test.method} terminó con {rows[0].outcome} sin un fallo confirmado en la aserción del criterio.")
            evidence.diagnose("RESULTADO_DEL_CASO_NO_CONCLUYENTE", rows[0].error or rows[0].outcome)

    if not linked:
        reasons.append("En la fuente capturada no se encontró una prueba vinculada que compruebe la cancelación.")
    blocked = [item for item in evidence.diagnostics if item["codigo"] != "RESULTADO_DEL_CASO_NO_CONCLUYENTE"]
    if blocked:
        reasons.insert(0, "La recopilación presenta un problema de infraestructura o integridad.")
    elif "INCUMPLIDO" in outcomes:
        verdict = "INCUMPLIDO"
    elif "VERIFICADO" in outcomes:
        verdict = "VERIFICADO"

    next_step = {
        "VERIFICADO": None,
        "INCUMPLIDO": "Corregir la evaluación de renovaciones para excluir los contratos cancelados y repetir la prueba.",
        "EVIDENCIA_INSUFICIENTE": (
            "Revisar el diagnóstico de recopilación y repetir la evaluación." if blocked
            else "Ejecutar un caso de cancelación vinculado con Trait(\"Criterio\", \"REN-001\") y confirmar su resultado."
        ),
    }[verdict]
    return {"veredicto": verdict, "justificacion": " ".join(reasons), "referencias": support, "siguiente_paso": next_step}


def _evaluate_ren002(evidence: Evidence, tests: list[SourceTest], criterion_text: str) -> dict:
    blocked = [item for item in evidence.diagnostics if item["codigo"] != "RESULTADO_DEL_CASO_NO_CONCLUYENTE"]
    candidates = [t for t in tests if t.active_idempotent or "REN-002" in t.traits]
    if blocked or not candidates:
        return {
            "id": "REN-002",
            "texto": criterion_text,
            "rol": "secundario",
            "veredicto": "EVIDENCIA_INSUFICIENTE",
            "pruebas": [],
            "resumen": "Sin ejecución verificada para ventanas activas (30, 7 y 1 día) sin duplicados.",
        }
    test = candidates[0]
    rows = [row for row in evidence.results if row.method == test.method]
    if not test.active_idempotent or len(rows) < 3:
        return {
            "id": "REN-002",
            "texto": criterion_text,
            "rol": "secundario",
            "veredicto": "EVIDENCIA_INSUFICIENTE",
            "pruebas": [test.ref],
            "resumen": f"{test.method} no cubre aún las tres ventanas (30, 7 y 1 día) en el TRX.",
        }
    if any(row.outcome == "Failed" for row in rows):
        return {
            "id": "REN-002",
            "texto": criterion_text,
            "rol": "secundario",
            "veredicto": "INCUMPLIDO",
            "pruebas": [test.ref],
            "resumen": f"{test.method} falló al validar unicidad de avisos en contratos activos.",
        }
    if all(row.outcome == "Passed" for row in rows):
        return {
            "id": "REN-002",
            "texto": criterion_text,
            "rol": "secundario",
            "veredicto": "VERIFICADO",
            "pruebas": [test.ref],
            "resumen": f"{test.method} verificó {len(rows)} ventanas activas (30, 7 y 1 día) sin avisos duplicados.",
        }
    return {
        "id": "REN-002",
        "texto": criterion_text,
        "rol": "secundario",
        "veredicto": "EVIDENCIA_INSUFICIENTE",
        "pruebas": [test.ref],
        "resumen": f"{test.method} no completó todas sus ejecuciones en el TRX.",
    }


def _evaluate_custom_criterion(
    criterion_id: str, criterion_text: str, evidence: Evidence, tests: list[SourceTest]
) -> dict:
    blocked = [item for item in evidence.diagnostics if item["codigo"] != "RESULTADO_DEL_CASO_NO_CONCLUYENTE"]
    linked = [t for t in tests if criterion_id in t.traits]
    if blocked or not linked:
        return {
            "id": criterion_id,
            "texto": criterion_text,
            "rol": "backlog",
            "veredicto": "EVIDENCIA_INSUFICIENTE",
            "pruebas": [],
            "resumen": f"Sin prueba xUnit marcada con Trait(\"Criterio\", \"{criterion_id}\").",
        }
    test = linked[0]
    rows = [r for r in evidence.results if r.method == test.method]
    if not rows:
        verdict, summary = "EVIDENCIA_INSUFICIENTE", f"Sin ejecución TRX para {test.method}."
    elif any(r.outcome == "Failed" for r in rows):
        verdict, summary = "INCUMPLIDO", f"{test.method} registró fallo en el TRX."
    elif all(r.outcome == "Passed" for r in rows):
        verdict, summary = "VERIFICADO", f"{test.method} aprobó ({len(rows)} caso(s) en TRX)."
    else:
        verdict, summary = "EVIDENCIA_INSUFICIENTE", f"{test.method} quedó sin ejecutar."
    return {
        "id": criterion_id,
        "texto": criterion_text,
        "rol": "backlog",
        "veredicto": verdict,
        "pruebas": [test.ref],
        "resumen": summary,
    }


def evaluate_criteria_matrix(
    evidence: Evidence,
    tests: list[SourceTest],
    primary_verdict: dict,
    boards_criteria: list[dict] | None = None,
) -> dict:
    catalog: dict[str, str] = {
        CRITERION["id"]: CRITERION["texto"],
        SECONDARY_CRITERION["id"]: SECONDARY_CRITERION["texto"],
    }
    for item in boards_criteria or []:
        cid = str(item.get("id") or "").strip().upper()
        txt = str(item.get("texto") or "").strip()
        if re.fullmatch(r"REN-\d+", cid) and txt:
            catalog[cid] = txt

    items = [
        {
            "id": "REN-001",
            "texto": catalog["REN-001"],
            "rol": "primario",
            "veredicto": primary_verdict["veredicto"],
            "pruebas": [ref["id"] for ref in primary_verdict["referencias"]],
            "resumen": primary_verdict["justificacion"],
        },
        _evaluate_ren002(evidence, tests, catalog["REN-002"]),
    ]
    for cid, txt in catalog.items():
        if cid not in {"REN-001", "REN-002"}:
            items.append(_evaluate_custom_criterion(cid, txt, evidence, tests))

    verified = sum(1 for item in items if item["veredicto"] == "VERIFICADO")
    # 4 escenarios del dominio Renovaciones: 3 ventanas activas idempotentes (30, 7, 1) + 1 contrato cancelado.
    ren2_ok = items[1]["veredicto"] == "VERIFICADO"
    ren1_ok = items[0]["veredicto"] == "VERIFICADO"
    scenarios_ok = (3 if ren2_ok else 0) + (1 if ren1_ok else 0)
    cobertura_xml = evidence.identity.get("cobertura_xml")
    return {
        "criterios_evaluados": items,
        "cobertura": {
            "criterios_verificados": verified,
            "criterios_totales": len(items),
            "criterios_pct": round((verified / len(items)) * 100, 1) if items else 0.0,
            "escenarios_dominio_verificados": scenarios_ok,
            "escenarios_dominio_totales": 4,
            "escenarios_dominio_pct": round((scenarios_ok / 4) * 100, 1),
            "cobertura_xml": cobertura_xml,
        },
    }
