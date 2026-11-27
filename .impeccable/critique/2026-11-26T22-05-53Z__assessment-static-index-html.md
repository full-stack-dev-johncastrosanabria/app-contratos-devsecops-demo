---
target: assessment/static/index.html
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html"
target_fingerprint: "sha256:aa62f3ba3493918d8295003d540908717104d6a7877b25dbd17910cdb5ffb4a2"
target_path: /Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html
timestamp: 2026-11-26T22-05-53Z
slug: assessment-static-index-html
---
Method: dual-agent (A: a9371bebc0ea827b5 · B: ab72e41f39d258f96)

#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | `?` below the fold opens drawer off-screen; rail loop never says which version is running; filter copy overwrites cache provenance in status banner |
| 2 | Match System / Real World | 3 | Raw enums leak in inspector (`EVIDENCIA_INSUFICIENTE`, `INCUMPLIDO`); evaluated stages announced as "Sin evaluar" |
| 3 | User Control and Freedom | 3 | Esc aborts the live run before closing inspector/drawer; Esc does not cancel the Boards confirm step |
| 4 | Consistency and Standards | 2 | One amber state named Atención / Pendiente / Evidencia insuficiente; informativo = "Sin evaluar" vs "informativas"; toolbar items move with message length |
| 5 | Error Prevention | 2 | Single key R starts a token-spending run (WCAG 2.1.4); confirm step focuses "Confirmar" (Enter-Enter writes Boards); "Detener :5080" unconfirmed; "v1 activa" relaunches |
| 6 | Recognition Rather Than Recall | 3 | Pip order v1·v2·v3 must be remembered; legend omits Pendiente/Informativo; inspector scroll hides corridor |
| 7 | Flexibility and Efficiency | 3 | V-tabs / Anterior / Siguiente move focus to the section; shortcuts cannot be disabled; no deep link |
| 8 | Aesthetic and Minimalist Design | 2 | Env-scoped stages 3/5/6/7 repeated identically in 3 columns; sandbox console = 44% of mobile first viewport |
| 9 | Error Recovery | 3 | Specific errors with retry; clipboard fallback writes to a possibly off-screen banner |
| 10 | Help and Documentation | 3 | Guide does not define the five stage states; shortcuts as prose |
| **Total** | | **27/40** | **Good** |

#### Design Specificity Verdict

**LLM assessment**: Built for this product. Two-line DevSec/CloudOps corridor meeting at the "Núcleo determinista" hub with v1·v2·v3 pips, governance questions per station, xUnit proof band with REN-001 tags, SHA-256 counts and copyable WIQL fingerprint, HITL with mandatory note. Generic residue: outlined cards with pill badges and outline-button rows still read as a SaaS card grid rather than a certification ledger.

**Deterministic scan**: `impeccable detect --json assessment/static/index.html` → 1 finding (`cramped-padding` on `.sandbox-strip`), judged false positive: measured insets 11–29px at 390px, ~72px derived at 1440px. Browser overlay blocked by CSP `script-src 'self'` (not bypassed). Measured: 0 overflow at 1440/390, 0 real targets <44px, 0 text pairs <4.5:1, 22/22 Tab stops with 3px ring, `[hidden]` honoured, reduced motion → 0 animations, console 0 errors.

#### Overall Impression

Big step from 18: the corridor + inline inspector is a product-specific wayfinding model, the deterministic proof band precedes agent narrative, and motion is tokenised and reduced-motion safe. What holds it below 32: unsafe keyboard/Esc model around costly actions, the comparative answer arriving late and diluted by duplicated environment rows, colour-only pips, and an inconsistent state vocabulary.

#### What's Working

1. Corridor + inspector: 8 stations on two lines, directional slide between stations, focus returns to the exact opener, full keyboard model.
2. Evidence before generative opinion: xUnit cases with REN-001 tag, failed case flagged with glyph + text, agent narratives collapsed; subgrid aligns bands across v1/v2/v3.
3. Disciplined motion: 140/240/320 ms tokens, expo-out, all keyframes gated by `prefers-reduced-motion: no-preference`, running state is the strongest moment.

#### Priority Issues

1. **[P1] Keyboard/Esc model unsafe around costly and irreversible actions** — Esc layering (confirm → inspector → drawer → run), R must not launch a run, confirm step focuses Cancelar and Esc cancels (`/impeccable harden`).
2. **[P1] Comparative answer arrives late and diluted** — verdict strip under the command deck, environment-scoped identical stages pulled out of per-version rows, compact sandbox on mobile (`/impeccable distill`).
3. **[P1] Per-version pips colour-only and <3:1** — glyph pips ✓ × ! – with ink outline, darker tokens, per-version states in station accessible name, legend completes all states (`/impeccable audit`).
4. **[P2] Inconsistent / inaccurate state vocabulary** — single dictionary Verificado / Incumplido / Evidencia insuficiente / Atención requerida / Informativo; never print backend enums; document states in guide (`/impeccable clarify`).
5. **[P2] Focus and viewport continuity in the interaction layer** — keep focus on activated V-tab/step control, refocus after D, scroll drawer into view, inspector scroll keeps station visible, active-version signal during runs (`/impeccable animate`).

#### Persona Red Flags

- **Alex (power user)**: V-tab/Siguiente click drops focus to section; Esc during run kills it; R from any button starts a paid run; Enter-Enter writes Boards.
- **Sam (screen reader)**: pips aria-hidden, station name gives only worst state; "Sin evaluar" on evaluated stages; single-key shortcuts conflict with speech input (2.1.4).
- **Casey (mobile 390)**: masthead 44% of first viewport, red "Detener" is the biggest target; first verdict 2.4 screens down, v3 6.7 screens down.

#### Minor Observations

- INCUMPLIDO gets the same celebratory stamp-pop as VERIFICADO.
- Card summary does not reflect the active "Solo brechas" filter.
- Copy button shrinks 225→95px on "Copiado"; run label change resizes neighbours.
- Help drawer puts 5 columns in a 4-column grid; governance placeholder truncated; text <12px on mobile (code 11.4px, kbd 11.2px).
- Esc after stepping 4→6 returns focus to station 4, not 6.

#### Questions to Consider

- Stage 3 (8 open CodeQL alerts) and stage 7 (27.78% 5xx) are styled neutral under a green v1 — is "informativo" hiding risk from the CISO?
- Should environment-scoped stages form one shared band the three versions stand on?
- Should a regression land differently from a pass in the motion language?
- Do start/stop controls for :5080 belong in the permanent masthead of a certification surface?
