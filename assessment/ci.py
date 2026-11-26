"""Valida la evidencia esperada de cada versión de la demo en CI."""
import argparse
from collections import Counter
from pathlib import Path

from .evidence import Evidence, collect
from .policy import evaluate, source_tests

EXPECTED = {
    "v1": ("VERIFICADO", 0, 4, 0),
    "v2": ("INCUMPLIDO", 1, 3, 1),
    "v3": ("EVIDENCIA_INSUFICIENTE", 0, 3, 0),
}


def matches_expected(evidence: Evidence, version: str) -> bool:
    verdict, exit_code, min_passed, failed = EXPECTED[version]
    actual = evaluate(evidence, source_tests(evidence.sources))
    outcomes = Counter(row.outcome for row in evidence.results)
    print(f"{version} · {actual['veredicto']} · {dict(outcomes)} · {evidence.directory}")
    for diagnostic in evidence.diagnostics:
        print(f"{diagnostic['codigo']} · {diagnostic['detalle']}")
    return (
        not evidence.diagnostics
        and actual["veredicto"] == verdict
        and evidence.identity["codigo_dotnet"] == exit_code
        and outcomes["Passed"] >= min_passed
        and outcomes["Failed"] == failed
        and sum(outcomes.values()) == outcomes["Passed"] + outcomes["Failed"]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", choices=EXPECTED)
    parser.add_argument("salida", type=Path)
    args = parser.parse_args()
    evidence = collect(Path(args.version), args.salida)
    if not matches_expected(evidence, args.version):
        parser.exit(1, f"{args.version}: la evidencia xUnit difiere de la esperada para la demo.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
