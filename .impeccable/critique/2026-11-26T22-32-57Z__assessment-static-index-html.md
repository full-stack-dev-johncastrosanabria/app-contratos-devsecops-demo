---
target: assessment/static/index.html
total_score: 29
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:/Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html"
target_fingerprint: "sha256:5a981eff3c69e86859901418b018226050ff2c28b95fe7554e77c8c4fb363375"
target_path: /Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html
timestamp: 2026-11-26T22-32-57Z
slug: assessment-static-index-html
---
Method: dual-agent (A: a358cce4af8a1c063 · B: a42b5fbe7567e377a)

#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Status banner below the fold at 1440×900; verdict strip does not say it is cached; failed initial load reports sandbox as stopped |
| 2 | Match System / Real World | 3 | `PENDIENTE_APROBACION` and "Alcance: version" leak in secondary layers; MAF/HITL/TRX undefined; 8 CodeQL alerts and 27.78% 5xx labelled "Informativo" |
| 3 | User Control and Freedom | 3 | `?` deep in the matrix jumps to top with no way back; "Probar vX (:5080)" replaces the live subject in one click |
| 4 | Consistency and Standards | 2 | Two glyph sets for the same states (legend `!`/`–` vs badges `⚠`/`ⓘ`); "Asegurar origen" vs "Asegurar desde el origen"; one action with three labels |
| 5 | Error Prevention | 3 | "Evaluar vX" spends tokens in one click without showing the engine; card/inspector launches not guarded |
| 6 | Recognition Rather Than Recall | 3 | Pips carry no version labels; engine choice must be remembered for per-card runs |
| 7 | Flexibility and Efficiency | 3 | No deep link to stage/version/filter; no key for V1/V2/V3 in inspector; no batch governance |
| 8 | Aesthetic and Minimalist Design | 3 | Stage rows repeat the state; subgrid leaves ~1000px blank when a disclosure opens; disabled "v1 activa" is brightest header element |
| 9 | Error Recovery | 3 | Governance errors exemplary; initial-load failure has no retry and misstates sandbox |
| 10 | Help and Documentation | 3 | Guide covers verdicts, five states, scopes, WIQL, shortcuts; dense block pushes controls down; jargon undefined |
| **Total** | | **29/40** | **Good** |

#### Design Specificity Verdict

**LLM assessment**: Authored for this product: two-line DevSec/CloudOps corridor with per-delivery pips, deterministic TRX proof band with the deciding REN-001 case tagged, copyable WIQL fingerprint, HITL confirmation naming the fingerprint and AB#1. Generic residue: card/badge/pill primitives and the decorative, non-interactive hub.

**Deterministic scan**: `impeccable detect --json assessment/static/index.html` → 1 finding (`cramped-padding` on `.sandbox-strip`, same false positive as before). Overlay blocked by CSP (not bypassed). Measured: 0 overflow at 1440/390, 0 targets <44px, 0 text pairs <4.5:1 (324 elements), 45/45 Tab stops with ring, `[hidden]` honoured, reduced motion → 0 animations. Fix checks confirmed: Esc layering, R focus-only, glyph pips 5.35–5.72:1, unified five-state names. New: status-banner dot fails 3:1 in pass/warn tones; eco-pill focus ring clipped at 390px; unguarded localStorage access.

#### Priority Issues

1. **[P1] Agent-reported security risk shown as neutral** — v1 "Verificado / Entrega conforme" while collapsed SecOps holds "Severidad: Alta" (8 CodeQL alerts, critical py/redos) in the same blue pill as "Informativa"; stations 3 and 7 grey for all deliveries. Fix: severity tokens/glyphs, high-severity count in card head, chips claim "REN-001 verificado" only.
2. **[P2] Split state vocabulary** — one STATE→glyph map for pips and badges, "Sin datos" in legend, distinct Atención hue/ring, humanize every backend enum.
3. **[P2] Inspector 1000px from the row that opened it** — inline/docked detail for matrix rows; move "Solo brechas" and status into the command bar.
4. **[P2] Untrue UI states after transitions** — abort leaves queued cards "En cola" and drops them from the strip; after a governance decision stages re-render without the shared set (common stages duplicated); failed load misstates sandbox.
5. **[P2] Scattered live-process controls** — single collapsed "Gestionar :5080" entry, same guard for card/inspector launches, show engine on "Evaluar vX".

#### Questions to Consider

- Should the v1 chip read "REN-001 verificado" so it claims only what it proves, given a high-severity CodeQL alert?
- Is the transit metaphor worth its translation cost versus a plain 8-column strip aligned to the cards?
- Should :5080 start/stop live in the evaluator masthead on every view?
- Why does the inspector sit 1000px above the matrix row that opens it most often?
