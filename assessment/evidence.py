"""Recopilación local y lectura del TRX de VSTest/xUnit."""
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4
import xml.etree.ElementTree as ET

PROJECT = Path("tests/Contratos.Tests/Contratos.Tests.csproj")
APP = Path("src/Contratos")
TRX_NS = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
CRITERION = {"id": "REN-001", "texto": "Al evaluar renovaciones, un contrato cancelado no debe generar un aviso"}


@dataclass
class Result:
    test_id: str
    execution_id: str
    name: str
    method: str
    outcome: str
    error: str
    stack: str


@dataclass
class Evidence:
    root: Path
    directory: Path
    identity: dict
    sources: dict[str, str] = field(default_factory=dict)
    results: list[Result] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)

    def diagnose(self, code: str, detail: str) -> None:
        self.diagnostics.append({"codigo": code, "detalle": detail})


def read_trx(path: Path, assembly: Path) -> tuple[str, str, list[Result]]:
    tree = ET.parse(path).getroot()
    summary = tree.find("t:ResultSummary", TRX_NS)
    counters = tree.find("t:ResultSummary/t:Counters", TRX_NS)
    if tree.tag != f"{{{TRX_NS['t']}}}TestRun" or not tree.get("id") or summary is None or counters is None:
        raise ValueError("Falta la identidad o el resumen de TestRun")

    definitions = {}
    for definition in tree.findall("t:TestDefinitions/t:UnitTest", TRX_NS):
        execution = definition.find("t:Execution", TRX_NS)
        method = definition.find("t:TestMethod", TRX_NS)
        if execution is None or method is None:
            raise ValueError("Definición TRX sin ejecución o método")
        key = (definition.get("id"), execution.get("id"))
        reported_assembly = Path(method.get("codeBase", ""))
        if (not all(key) or key in definitions or reported_assembly.resolve() != assembly
                or not method.get("adapterTypeName", "").startswith("executor://xunit/")
                or not method.get("className") or not method.get("name")):
            raise ValueError("Definición TRX ambigua o ajena al ensamblado xUnit de la ejecución")
        definitions[key] = f"{method.get('className')}.{method.get('name')}"

    entries = Counter((node.get("testId"), node.get("executionId"))
                      for node in tree.findall("t:TestEntries/t:TestEntry", TRX_NS))
    results = []
    used = set()
    for node in tree.findall("t:Results/t:UnitTestResult", TRX_NS):
        key = (node.get("testId"), node.get("executionId"))
        if key not in definitions or entries[key] != 1 or key[1] in used or not node.get("outcome"):
            raise ValueError("Resultado TRX sin correlación única por testId y executionId")
        used.add(key[1])
        results.append(Result(*key, node.get("testName", ""), definitions[key], node.get("outcome"),
                              node.findtext("t:Output/t:ErrorInfo/t:Message", "", TRX_NS),
                              node.findtext("t:Output/t:ErrorInfo/t:StackTrace", "", TRX_NS)))
    if len(results) != int(counters.get("total", "")):
        raise ValueError("El total TRX no coincide con los resultados individuales")
    return tree.attrib["id"], summary.get("outcome", ""), results


def snapshot(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    hashes, sources = {}, {}
    for base in (APP, PROJECT.parent):
        if (root / base).resolve() != root / base:
            raise ValueError(f"El árbol del proyecto contiene un enlace simbólico: {base}")
        for folder, dirs, files in os.walk(root / base):
            dirs[:] = sorted(set(dirs) - {"bin", "obj", "TestResults"})
            for name in sorted(dirs + files):
                if (Path(folder) / name).is_symlink():
                    raise ValueError(f"Enlace simbólico fuera del alcance de la captura: {name}")
            for name in sorted(files):
                path = Path(folder) / name
                relative = path.relative_to(root).as_posix()
                content = path.read_bytes()
                hashes[relative] = sha256(content).hexdigest()
                if path.suffix == ".cs" and path.is_relative_to(root / PROJECT.parent):
                    sources[relative] = content.decode("utf-8-sig")
    return hashes, sources


def git_identity(root: Path) -> dict:
    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        except FileNotFoundError:
            return None
        return result.stdout.rstrip("\n") if result.returncode == 0 else None

    commit = git("rev-parse", "--verify", "HEAD")
    status = git("status", "--porcelain", "--untracked-files=normal", "--", ".")
    return {"commit": commit, "cambios_locales": None if status is None else bool(status),
            "estado_git_del_proyecto": status}


def collect(root: Path, output: Path) -> Evidence:
    root = root.resolve()
    directory = output.resolve() / uuid4().hex
    directory.mkdir(parents=True)
    evidence = Evidence(root, directory, {
        "id": directory.name, "version": root.name, "proyecto": str(root / PROJECT),
    })
    identity = evidence.identity
    identity.update(git_identity(root))
    trx = directory / "resultados.trx"
    artifacts = directory / "build"
    log_path = directory / "dotnet-test.log"
    command = ["dotnet", "test", str(root / PROJECT), "--artifacts-path", str(artifacts),
               "--configuration", "Debug", "-p:ContinuousIntegrationBuild=false",
               "--logger", f"trx;LogFileName={trx.name}", "--results-directory", str(directory)]
    identity.update(comando=command, trx=None, trx_id=None, codigo_dotnet=None, log=log_path.name)
    try:
        if not (root / PROJECT).is_file() or not (root / APP).is_dir():
            raise ValueError(f"No se encontró la estructura del proyecto en {root}")
        identity["sha256_archivos"], evidence.sources = snapshot(root)
    except (OSError, ValueError) as exc:
        evidence.diagnose("PROYECTO_ILEGIBLE", str(exc))
        identity["log"] = None
        return evidence

    env = {key: value for key, value in os.environ.items() if not key.startswith(("AZURE_OPENAI_", "ANTHROPIC_"))}
    env.update(DOTNET_CLI_UI_LANGUAGE="en", VSLANG="1033", LC_MESSAGES="C")
    with log_path.open("wb") as log:
        try:
            result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            identity["codigo_dotnet"] = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            evidence.diagnose("DOTNET_NO_COMPLETADO", type(exc).__name__)

    if trx.is_file():
        identity["trx"] = trx.name
        try:
            identity["sha256_trx"] = sha256(trx.read_bytes()).hexdigest()
            assembly = (artifacts / "bin" / PROJECT.stem / "debug" / f"{PROJECT.stem}.dll").resolve()
            identity["trx_id"], outcome, evidence.results = read_trx(trx, assembly)
            if outcome not in {"Completed", "Passed", "Failed"}:
                evidence.diagnose("TRX_EJECUCION_INCOMPLETA", f"Resultado global de VSTest: {outcome}")
        except (OSError, ET.ParseError, ValueError) as exc:
            evidence.diagnose("TRX_INVALIDO", str(exc))
    else:
        evidence.diagnose("TRX_AUSENTE", "dotnet test no produjo un TRX en esta ejecución")

    if identity["codigo_dotnet"] not in (0, None):
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\berror (?:CS|MSB|NETSDK|NU)\d+\b", log_text, re.I):
            evidence.diagnose("ERROR_COMPILACION_O_RESTAURACION", "Revisar los errores de compilación o restauración en el log")
        elif not any(row.outcome == "Failed" for row in evidence.results):
            evidence.diagnose("DOTNET_ERROR", "dotnet test devolvió un código distinto de cero sin un caso fallido correlacionado")

    try:
        if snapshot(root)[0] != identity["sha256_archivos"] or git_identity(root)["commit"] != identity["commit"]:
            evidence.diagnose("FUENTE_CAMBIO", "Los archivos del proyecto o el commit cambiaron durante la ejecución")
    except (OSError, ValueError) as exc:
        evidence.diagnose("FUENTE_CAMBIO", str(exc))
    return evidence
