"""Correlación de fuentes y política determinista para REN-001."""
from collections import Counter
from dataclasses import dataclass
import re

from .evidence import Evidence, Result

STRING = r'"(?:[^"\\\n]|\\.)*"'
TOKEN = re.compile(rf'{STRING}|//[^\n]*|/\*[\s\S]*?\*/')
HEADER = re.compile(r"\s*using\s+Xunit\s*;\s*public\s+class\s+(\w+)\s*\{")
TEST = re.compile(
    r'(?P<attrs>(?:\[\s*\w+(?:\s*\([^\n]*?\))?\s*\]\s*)+)'
    r'public\s+void\s+(?P<name>\w+)\s*\((?P<params>[^()]*)\)\s*'
    r'\{(?P<body>[^{}]*)\}'
)
TRAIT = re.compile(r'\[\s*Trait\s*\(\s*"Criterio"\s*,\s*"REN-001"\s*\)\s*\]')
FACT = re.compile(r'\[\s*Fact\s*\]')
FIXTURE = re.compile(
    r'static\s+Datos\s+Caso\s*\(\s*bool\s+cancelado\s*,\s*int\s+dias\s*\)\s*=>\s*new\s*\('
    rf'\s*\[\s*new\s+Contrato\s*\(\s*Guid\.NewGuid\(\)\s*,\s*{STRING}\s*,\s*{STRING}\s*,\s*{STRING}'
    r'\s*,\s*Hoy\.AddDays\(dias\)\s*,\s*cancelado\s*\)\s*\]\s*,\s*\[\s*\]\s*\)\s*;'
)
SCENARIO = re.compile(
    r'\s*var\s+(\w+)\s*=\s*Caso\s*\(\s*true\s*,\s*(?:1|7|30)\s*\)\s*;'
    r'\s*Renovaciones\.Evaluar\s*\(\s*\1\s*,\s*Hoy\s*\)\s*;'
    r'\s*(?P<assertion>Assert\.Empty)\s*\(\s*\1\s*\.\s*Avisos\s*\)\s*;\s*'
)
EMPTY_FAILURE = re.compile(r'^Assert\.Empty\(\) Failure: Collection was not empty\s+Collection: \[Aviso \{')


@dataclass(frozen=True)
class SourceTest:
    file: str
    line: int
    method: str
    linked: bool
    code: str
    fixture: str
    assertion_line: int | None

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
        braces = re.compile(rf'{STRING}|[{{}}]')
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

        fixture = next((m for m in FIXTURE.finditer(clean, header.end(), end) if direct_member(m.start())), None)
        for match in TEST.finditer(clean, header.end(), end):
            attrs = match["attrs"]
            if not direct_member(match.start()) or not re.search(r"\[\s*(?:Fact|Theory)\b", attrs):
                continue
            linked = TRAIT.search(attrs) is not None
            scenario = SCENARIO.fullmatch(match["body"])
            assertion_line = None
            if (linked and FACT.search(attrs) and not match["params"].strip() and fixture and scenario
                    and not re.search(r"^\s*#", clean, re.M)):
                assertion_line = clean.count("\n", 0, match.start("body") + scenario.start("assertion")) + 1
            tests.append(SourceTest(path, clean.count("\n", 0, match.start()) + 1,
                                    f"{header[1]}.{match['name']}", linked,
                                    source[match.start():match.end()],
                                    source[fixture.start():fixture.end()] if fixture else "", assertion_line))
    return tests


def is_criterion_failure(row: Result, test: SourceTest, evidence: Evidence) -> bool:
    if not EMPTY_FAILURE.match(row.error):
        return False
    frame = re.compile(rf"^\s*at {re.escape(test.method)}\(\) in (.+):line (\d+)\s*$")
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
