"""Reversibilidad integral para múltiples sesiones de demostración (local, corridas y Azure Boards)."""
from datetime import datetime, timezone
import re
import shutil
from pathlib import Path
import urllib.error
import urllib.parse

from .integrations import _ado_headers, _http_json, load_settings

CANONICAL_CRITERIA_HTML = (
    "<ul>"
    "<li><b>REN-001:</b> Al evaluar renovaciones, un contrato cancelado no debe generar un aviso.</li>"
    "<li><b>REN-002:</b> Al evaluar contratos activos a 30, 7 y 1 día, evaluaciones repetidas el mismo día generan un único aviso sin duplicados.</li>"
    "</ul>"
)


def list_archived_sessions(runs_dir: Path) -> list[str]:
    archive_root = runs_dir / "_archivo_demos"
    if not archive_root.is_dir():
        return []
    return sorted(
        (d.name for d in archive_root.iterdir() if d.is_dir() and not d.name.startswith(".")),
        reverse=True,
    )


def clean_sandbox_data(repo_root: Path) -> list[str]:
    removed: list[str] = []
    for ver in ("v1", "v2", "v3"):
        app_dir = repo_root / ver / "src" / "Contratos"
        if not app_dir.is_dir():
            continue
        for candidate in app_dir.glob("datos.json*"):
            if candidate.is_file():
                candidate.unlink()
                removed.append(candidate.relative_to(repo_root).as_posix())
    return removed


def archive_runs(runs_dir: Path) -> dict:
    if not runs_dir.is_dir():
        return {"archivadas": 0, "sesion_archivo": None}
    run_folders = [
        d for d in runs_dir.iterdir()
        if d.is_dir() and re.fullmatch(r"[0-9a-f]{32}", d.name)
    ]
    if not run_folders:
        return {"archivadas": 0, "sesion_archivo": None}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_root = runs_dir / "_archivo_demos"
    dest = archive_root / stamp
    suffix = 1
    while dest.exists():
        suffix += 1
        dest = archive_root / f"{stamp}-{suffix}"
    dest.mkdir(parents=True, exist_ok=True)

    for folder in run_folders:
        shutil.move(str(folder), str(dest / folder.name))

    ckpt_dir = runs_dir / "_checkpoints"
    if ckpt_dir.is_dir():
        shutil.move(str(ckpt_dir), str(dest / "_checkpoints"))

    return {"archivadas": len(run_folders), "sesion_archivo": dest.name}


def restore_latest_archive(runs_dir: Path, session_name: str | None = None) -> dict:
    sessions = list_archived_sessions(runs_dir)
    if not sessions:
        raise FileNotFoundError("No existen sesiones archivadas para restaurar.")
    chosen = session_name if session_name in sessions else sessions[0]
    src = runs_dir / "_archivo_demos" / chosen
    if not src.is_dir():
        raise FileNotFoundError(f"No se encontró la sesión archivada {chosen}.")

    # Si hay corridas activas actuales, archivarlas antes salvo que estemos vacíos.
    active = [d for d in runs_dir.iterdir() if d.is_dir() and re.fullmatch(r"[0-9a-f]{32}", d.name)] if runs_dir.is_dir() else []
    previous_backup = None
    if active:
        previous_backup = archive_runs(runs_dir).get("sesion_archivo")

    runs_dir.mkdir(parents=True, exist_ok=True)
    restored = 0
    for item in src.iterdir():
        target = runs_dir / item.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), str(target))
        if re.fullmatch(r"[0-9a-f]{32}", item.name):
            restored += 1

    src.rmdir()
    pbi_sync = None
    if (runs_dir / "_estado_powerbi.json").is_file():
        try:
            from .powerbi_cloud import sync_powerbi_cloud
            pbi_sync = sync_powerbi_cloud(runs_dir, ensure_report=False)
        except Exception:
            pbi_sync = None
    return {
        "sesion_restaurada": chosen,
        "corridas_restauradas": restored,
        "respaldo_previo": previous_backup,
        "powerbi": pbi_sync,
        "archivos_disponibles": list_archived_sessions(runs_dir),
    }


def wiql_tareas_demo(project: str) -> dict:
    """Tareas de demo que siguen vivas en Boards: las que el reinicio envía a la papelera."""
    return {
        "query": (
            f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{project}' "
            "AND [System.WorkItemType] = 'Task' "
            "AND ([System.Tags] CONTAINS 'DevSecOps-Agent' OR [System.Tags] CONTAINS 'devsecops-fp-') "
            "AND [System.State] <> 'Removed'"
        )
    }


def reset_boards_demo_state(settings: dict[str, str] | None = None) -> dict:
    cfg = settings or load_settings()
    org = cfg.get("AZURE_DEVOPS_ORG_URL", "").rstrip("/")
    project = cfg.get("AZURE_DEVOPS_PROJECT", "")
    wi_id = cfg.get("AZURE_DEVOPS_WORK_ITEM_ID") or "1"
    if not org or not project:
        return {"disponible": False, "motivo": "Azure Boards no configurado en assessment/.env."}
    headers = _ado_headers(cfg)
    patch_headers = _ado_headers(cfg, content_type="application/json-patch+json")
    if not headers or not patch_headers:
        return {"disponible": False, "motivo": "Sin credenciales activas para reiniciar Azure Boards."}

    proj_enc = urllib.parse.quote(project)
    found = _http_json("POST", f"{org}/{proj_enc}/_apis/wit/wiql?api-version=7.1", headers, wiql_tareas_demo(project))
    items = found.get("workItems") or []
    removed_ids: list[int] = []
    methods: dict[str, str] = {}
    for entry in items:
        tid = entry["id"]
        item_url = f"{org}/{proj_enc}/_apis/wit/workitems/{tid}?api-version=7.1"
        try:
            # Sin destroy: la tarea va a la papelera de Boards y se puede restaurar.
            _http_json("DELETE", item_url, headers)
            methods[f"AB#{tid}"] = "papelera"
        except urllib.error.HTTPError as exc:
            if exc.code not in (401, 403):
                raise
            _http_json(
                "PATCH",
                item_url,
                patch_headers,
                [
                    {"op": "add", "path": "/fields/System.State", "value": "Removed"},
                    {
                        "op": "add",
                        "path": "/fields/System.History",
                        "value": "<p>Tarea retirada (<code>Removed</code>) al reiniciar el entorno para una nueva sesión de demostración.</p>",
                    },
                ],
            )
            methods[f"AB#{tid}"] = "removed"
        removed_ids.append(tid)

    # Restaurar AB#1 a su estado canónico limpio
    _http_json(
        "PATCH",
        f"{org}/{proj_enc}/_apis/wit/workitems/{wi_id}?api-version=7.1",
        patch_headers,
        [
            {"op": "add", "path": "/fields/System.State", "value": "Active"},
            {"op": "add", "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria", "value": CANONICAL_CRITERIA_HTML},
            {"op": "add", "path": "/fields/System.Tags", "value": "REN-001; REN-002; DevSecOps"},
        ],
    )
    return {
        "disponible": True,
        "historia_restaurada": f"AB#{wi_id}",
        "tareas_retiradas": [f"AB#{tid}" for tid in removed_ids],
        "cantidad_tareas_retiradas": len(removed_ids),
        "metodo_por_tarea": methods,
    }


def revert_single_boards_task(work_item_id: int, target_state: str = "Removed", settings: dict[str, str] | None = None) -> dict:
    cfg = settings or load_settings()
    org = cfg.get("AZURE_DEVOPS_ORG_URL", "").rstrip("/")
    project = cfg.get("AZURE_DEVOPS_PROJECT", "")
    if not org or not project:
        return {"sincronizado": False}
    patch_headers = _ado_headers(cfg, content_type="application/json-patch+json")
    if not patch_headers:
        return {"sincronizado": False}
    proj_enc = urllib.parse.quote(project)
    _http_json(
        "PATCH",
        f"{org}/{proj_enc}/_apis/wit/workitems/{work_item_id}?api-version=7.1",
        patch_headers,
        [
            {"op": "add", "path": "/fields/System.State", "value": target_state},
            {
                "op": "add",
                "path": "/fields/System.History",
                "value": f"<p>Estado revertido a <code>{target_state}</code> para repetir demostración en vivo.</p>",
            },
        ],
    )
    return {"sincronizado": True, "work_item_id": work_item_id, "nuevo_estado": target_state}


def execute_demo_reset(
    repo_root: Path,
    runs_dir: Path,
    *,
    reset_runs: bool = True,
    reset_sandbox: bool = True,
    reset_boards: bool = False,
    reset_code: bool = True,
    reset_github_prs: bool = True,
    sync_powerbi: bool = False,
) -> dict:
    from .remediation import close_github_remediation_prs, revert_local_remediation

    summary: dict = {
        "ejecutado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "corridas": {"archivadas": 0, "sesion_archivo": None},
        "sandbox_archivos_limpiados": [],
        "codigo_revertido": [],
        "prs_cerrados": [],
        "boards": None,
        "powerbi": None,
        "archivos_disponibles": [],
    }
    if reset_code:
        from .vulnerabilities import revert_vuln_remediation
        summary["codigo_revertido"] = revert_local_remediation(repo_root, runs_dir, version=None)
        vuln_rev = revert_vuln_remediation(repo_root, runs_dir, vuln_id=None)["archivos_revertidos"]
        for path in vuln_rev:
            if path not in summary["codigo_revertido"]:
                summary["codigo_revertido"].append(path)
    if reset_github_prs:
        from .vulnerabilities import close_vuln_github_prs
        summary["prs_cerrados"] = close_github_remediation_prs(runs_dir, version=None) + close_vuln_github_prs(runs_dir, vuln_id=None)
    if reset_sandbox:
        summary["sandbox_archivos_limpiados"] = clean_sandbox_data(repo_root)
    if reset_runs:
        summary["corridas"] = archive_runs(runs_dir)
    if sync_powerbi and (runs_dir / "_estado_powerbi.json").is_file():
        try:
            from .powerbi_cloud import sync_powerbi_cloud
            summary["powerbi"] = sync_powerbi_cloud(runs_dir, ensure_report=False)
        except Exception:
            summary["powerbi"] = {"sincronizado": False}
    if reset_boards:
        summary["boards"] = reset_boards_demo_state()
    summary["archivos_disponibles"] = list_archived_sessions(runs_dir)
    return summary
