---
target: assessment/static/index.html
total_score: 18
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 4
target_identity: "file:/Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html"
target_fingerprint: "sha256:ac4ddd9aa378462b353b8e6ebada5966fd527d2eec4e3bbe08cec9c6ef60c524"
target_path: /Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html
timestamp: 2026-11-26T21-22-55Z
slug: assessment-static-index-html
---
Method: dual-agent (A: 1f7b0988-2918-452d-90ca-18d2c9a17ef6 · B: 9174105a-ee80-4b68-90ca-18d2c9a17ef6)

#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | Cached runs auto-load without timestamp/cache badge; sandbox boot lacks button progress; top map hides which version failed |
| 2 | Match System / Real World | 2 | Raw JSON keys in modal `<dt>`, mixed voseo/tuteo/English labels, and consumer emojis on an executive audit console |
| 3 | User Control and Freedom | 2 | No Cancel/Abort during long 3-version MAF runs; irreversible HITL decisions; no clickable `:5080` link fallback if popup blocked |
| 4 | Consistency and Standards | 2 | Server-mutating buttons use `↗` link arrows; duplicate `<h1>` in dialog; clicking red stage opens `v1` green data |
| 5 | Error Prevention | 1 | `Descartar` permanently resolves checkpoint with blank rationale and zero confirmation; double-clickable sandbox boot |
| 6 | Recognition Rather Than Recall | 2 | Individual xUnit test names (`resultados_trx[].name`) and SHA-256 counts hidden from cards; users must cross-reference raw XML/JSON |
| 7 | Flexibility and Efficiency | 2 | Zero keyboard shortcuts, no stage-diff filter (`24` open stage rows), no per-card re-run, no copy buttons for SHA/WIQL tags |
| 8 | Aesthetic and Minimalist Design | 2 | Hero + bridge + glowing dark cycle panel bury controls below the fold; 4-deep nested cards and emojis add visual noise |
| 9 | Error Recovery | 1 | Sandbox and HITL errors write to an off-screen pale-blue `#status` pill without `role="alert"`, error styling, or local retry |
| 10 | Help and Documentation | 2 | No inline reference for `REN-001.v2` certification rules, scope badges (`version`/`recurso`/`ambiente`), or WIQL idempotency |
| **Total** | | **18/40** | **Poor** |

#### Design Specificity Verdict

**LLM assessment**: Category-interchangeable AI SaaS dashboard relying on consumer emojis (`📋`, `🔀`, `🛡️`, `🧠 · 🔒 · 🏛️`), cyan outer glows, stacked monospace eyebrows, and 4-level Russian-doll cards instead of deterministic DevSecOps audit precision.

**Deterministic scan**: `impeccable detect --json assessment/static/index.html` returned 11 findings (6 warnings, 5 advisories): `dark-glow` (2 true positives on `.brand-mark` and `.hub-badge`, 1 false positive on dark header elevation shadow), `all-caps-body` (2 on `.loop-label`), `nested-cards` (1 static + 3-level runtime nesting), and `gpt-thin-border-wide-shadow` (5 ghost cards). CSS rules also include `4px` `side-tab` borders and 8+ interactive targets under 44px.

#### Priority Issues

1. **[P1] Worst-case top stage map opens `v1` passing data by default and duplicates 24 open stage boxes** — Fix: replace with a version-aware orthogonal 8-stage transit strip + inline station inspector, and collapse passing stages inside cards (`$impeccable distill`, `$impeccable layout`).
2. **[P1] Async `window.open` triggers popup blockers and lacks boot state or `:5080` fallback link** — Fix: synchronous named-window pre-open or direct clickable `:5080` link pill + disabled/loading state on sandbox controls (`$impeccable harden`).
3. **[P1] Irreversible HITL governance (`Aprobar`/`Descartar`) lacks confirmation, accepts blank dismissal notes, and hides errors off-screen** — Fix: require rationale for dismissal, add explicit inline confirmation + cancel, preserve keyboard focus, and render inline `role="alert"` errors (`$impeccable harden`, `$impeccable clarify`).
4. **[P1] Above-the-fold bloat, unaligned comparison columns, and blended AI/deterministic proof** — Fix: Operate-first workspace toolbar above the fold, CSS `subgrid` row alignment across `v1`/`v2`/`v3`, explicit cryptographic/xUnit proof vs. MAF agent commentary, and cached- vs. live-run badges (`$impeccable layout`, `$impeccable typeset`).
5. **[P2] Sub-44px touch targets, `<3:1` control border/focus contrast on navy, raw screen-reader glyphs, and 85 hardcoded CSS colors** — Fix: `>=44px` hit areas, high-contrast focus rings, SVG iconography with `aria-hidden="true"`, unified `:root` tokens, and full `prefers-reduced-motion` gating (`$impeccable audit`, `$impeccable polish`).
