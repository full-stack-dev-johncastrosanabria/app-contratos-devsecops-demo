---
target: assessment/static/index.html
total_score: 30
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:/Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html"
target_fingerprint: "sha256:981fa46b6a96251a203703bddb482a8eb1ed0addea2e45c9f11613123e428b4c"
target_path: /Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html
timestamp: 2026-11-27T01-41-02Z
slug: assessment-static-index-html
---
Method: dual-agent (A: a8ff83052f2ad086d · B: a88e93ed724725d45)

#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Mostly strong: live-region status, cached vs live provenance with timestamps, a running clock in the hub, an indeterminate bar on the busy card, sandbox state. The gap is the card quick action "v1 en ejecución" (it means the :5080 sandbox runs v1). It sits next to "Evaluar v1 · 0 tokens" and reads as "an evaluation of v1 is running". The word "ejecución" is shared with "Ejecutar evaluación" and "Ejecutando ahora…". |
| 2 | Match Between System and Real World | 3 | The copy contradicts itself on what certification means. Shared stage 3 says "8 alertas SAST abiertas: revisa su severidad en CodeQL antes de certificar", yet the closing banner says "v1 queda certificada para REN-001" and v1's chip shows "SecOps: 1 alta". The scoping (REN-001 certifies one rule) is sound, but the stage-3 wording breaks it. |
| 3 | User Control and Freedom | 3 | Esc closes each layer and returns focus (inspector goes back to the station or row, help goes back to its trigger). A run can be stopped with Esc×2 or the button, and the confirm step has Cancelar plus Esc. However, approve and discard are final after confirmation, with no grace or undo window. Re-running one delivery also wipes that card's previous evidence until it finishes, and the evidence is restored only on abort. |
| 4 | Consistency and Standards | 2 | Codes overlap. Stations are numbered 1–8 and keys 1–8 open them, but the pips under each station use "1·2·3" to mean v1·v2·v3, so the legend has to decode it. The same amber "?" glyph marks the delivery verdict "Evidencia insuficiente" and the stage state "Sin confirmar", and the help drawer needs a paragraph to tell them apart. Version tabs read "V1/V2/V3" while the rest of the page uses "v1". |
| 5 | Error Prevention | 4 | Excellent and verified live. Descartar with an empty note shows an inline error and focuses the field. Aprobar opens a confirmation that names AB#1 and the fingerprint, with Cancelar focused so a stray Enter cancels. A paid agent run needs a second press. R only focuses the run button. Replacing or stopping the sandbox needs arming. With cached runs present, the engine defaults to 0 tokens. One refinement: approval writes to Boards with an optional note, and the prompt does not say whether it will create or update the task. |
| 6 | Recognition Rather Than Recall | 3 | The legend, inline key hints and the per-version comparison in the inspector support recognition. Two memory bridges remain: the "1·2·3 = v1·v2·v3" pip code, and the card summary "6 comunes (1, 2, 3, 5, 6, 7) sobre la matriz", which asks you to remember which stage number is which and look up to a separate band. |
| 7 | Flexibility and Efficiency of Use | 4 | There are many power paths: keys 1–8, V, ←/→ (wrapping 8 to 1), D, R, ? and Esc, which can be switched off (meets WCAG 2.1.4). Views deep-link (#etapa=4&version=v2&filtro=brechas), any delivery can be evaluated from its card, and a stage opens from the station, a card row or a verified chip. The one gap for triage: ←/→ ignores "Solo brechas", and there is no "next gap" key. |
| 8 | Aesthetic and Minimalist Design | 2 | The first viewport is disciplined, but the cards are noisy. Each card is about 1,500px tall on desktop, has about 17 controls, and puts 5 equal-weight outlined artifact buttons directly under Aprobar/Descartar. The reason, next step, verdict strip and closing banner repeat the same conclusion. Subgrid alignment leaves about 300px of dead white space in v1. Measured on the page: 8 font weights and 127 bold text nodes, which flattens hierarchy. |
| 9 | Help Users Recognize, Diagnose, and Recover from Errors | 3 | The source shows plain Spanish errors with specific fixes ("confirma que «python -m assessment.ui» sigue en ejecución"), inline Reintentar buttons, an offer to retry a failed agent run with 0 tokens, and a governance failure message that keeps the note ("tu nota se conservó"). But a sandbox launch started from a card's "Iniciar vX en :5080" reports its error in the header alert strip, about 1,500px above the button. |
| 10 | Help and Documentation | 3 | The guide drawer is task-focused and well organized: verdicts, stage states, the REN-001.v2 recipe, scopes, WIQL and shortcuts, reachable with ?. The inspector adds a "Pregunta de gobierno" for each stage. But terms used inside the cards (WIQL, TRX, HITL, SHA-256, CSPM, KQL) are defined only inside the drawer, with no inline definition where they appear. |
| **Total** | | **30/40** | **Good** |

#### Anti-Patterns Verdict

Authored for this product, not interchangeable with others in the category. The page has three signature moves that only make sense for REN-001 certification. First, the three-chip verdict strip names the deciding xUnit test ("Prueba «cancelado no genera aviso»: fallida"). Second, the 8-station transit corridor splits into a DevSec line and a CloudOps line around a "Núcleo determinista" hub, with per-delivery pips. Third, the HITL governance block shows the devsecops-fp fingerprint inside its confirmation prompt. The navy masthead and sheets on an ice-blue canvas follow the brand commitment. The generic part is inside the delivery cards: equal outlined pill buttons, chips and bands, with 5 artifact buttons and bold 13px text everywhere. That skin could belong to any admin dashboard, so the specificity drops once you scroll past the corridor.

#### Overall Impression

Arrival: the navy masthead with live sandbox status reads as institutional and trustworthy. Within about 5 seconds the verdict strip delivers the peak: green, red and amber chips each with a one-line reason. Curiosity: the transit corridor invites exploration. Pressing 4 or clicking a station opens an inspector that compares all three deliveries, and the wrap-around arrows and Esc focus return feel crafted. Valley: scrolling into the matrix. Each card is a long stack of bold 13px text, outlined pills and repeated conclusions, and v1 has a blank gap. On mobile the comparison turns into an 8,000px scroll. A second, quieter valley comes for the security-minded reader: the gap filter hides the SAST and 5xx warnings, and \"certificada\" sits next to \"SecOps: 1 alta\", which plants doubt. Waiting (running state): the hub clock and pulsing rail reassure, but the running card empties to a bar, so the comparison disappears while it runs. High-stakes moment: governance is the best-handled emotional beat. The confirmation restates AB#1 and the fingerprint, Cancelar holds focus, and Esc backs out. End: the navy closing banner (\"v1 queda certificada… decidir las 2 acciones\" with jump buttons) is a strong peak-end close, weakened only by the certification wording contradiction.

#### What's Working

- Verdict strip as the 5-second answer. Three chips (v1 ✓ Verificado / v2 × Incumplido / v3 ? Evidencia insuficiente) carry glyph, color and text, name the deciding TRX test and the count of high SecOps findings, and sit above a one-line headline ("2 de 3 entregas con brecha · 2 acciones esperan revisión humana · corridas en caché"). Each chip jumps to its card. This delivers product principle 2 almost word for word.
- The transit corridor plus inspector is product-native and well engineered. Two lines meet at the deterministic hub, and a stage can be opened from a station, keys 1–8, a card row or a verified chip. The inspector frames each stage as a governance question, compares v1/v2/v3 side by side, deep-links through the URL hash, and returns focus to its origin on Esc. When opened from the matrix it docks as a bottom sheet with scroll-padding-block-end, so the originating row and later focus stay unobscured. On mobile the corridor reflows cleanly into 4 stations, the hub, then 4 stations, with every target at least 44px.
- HITL governance is designed for deliberate, safe decisions. The discard note is mandatory, with inline validation and focus. The confirmation step restates AB#1 and the fingerprint, puts default focus on Cancelar and closes on Esc. Paid runs need a second press, R never starts a run, and stopping or replacing the sandbox needs arming. The state shown is honest: "Corrida previa en caché · 26 nov, 14:39" against "Ejecutando ahora".

#### Priority Issues

**[P1] The meaning of "certified" and the gap filter conflict. "Solo brechas" (D) treats "Informativo" stages as non-gaps, so turning it on hides shared stage 3 ("8 alertas SAST abiertas: revisa su severidad en CodeQL antes de certificar") and stage 7 (27.78% 5xx with no baseline). The shared band drops to stages 5 and 6 only. Meanwhile the closing banner says "v1 queda certificada para REN-001" while v1's chip shows "SecOps: 1 alta" and stage 3 still says to review "antes de certificar".**

- Why: The audience includes CISOs, and the brief promises explicit scope for every finding. Their natural triage tool removes exactly the security warnings the page itself says must be reviewed, and the certification wording contradicts that same warning. In a live executive session this raises the question "is v1 certified or not?", which the UI cannot settle without the help drawer.
- Fix: Keep the single-rule model, but say it in the copy. Reword stage 3 to "8 alertas SAST abiertas · fuera del alcance de REN-001: revísalas antes de desplegar", and qualify the banner ("v1 queda certificada para REN-001 (1 hallazgo SecOps alto fuera de alcance)"). When the filter is on, state in its note what it hides ("2 señales informativas por revisar ocultas: etapas 3 y 7") and keep those rows as collapsed one-liners instead of removing them. Optionally add a separate "Por revisar" pip variant so informative-with-warning is visibly different from plain informative.
- Command: /impeccable clarify assessment/static/index.html

**[P2] The state and number vocabularies collide. Stations are 1–8, keys 1–8 open them, the pips under each station use "1·2·3" for v1·v2·v3, card summaries say "6 comunes (1, 2, 3, 5, 6, 7)", and the inspector tabs say "V1/V2/V3". On top of that, the same amber "?" glyph is used for the delivery verdict "Evidencia insuficiente" and the stage state "Sin confirmar", and v3 shows both for the same root cause. In all, six stage states and three verdicts share one color system.**

- Why: The page asks the reader to decode a legend before they can read the corridor, which works against the five-second STORY in the direction contract. The help drawer has to spend a paragraph separating "Sin confirmar" from "Evidencia insuficiente", which shows the two read as the same.
- Fix: Label the pips with the delivery names ("v1 ✓ v2 × v3 ?"), or drop the digits and rely on fixed column position with a single header row. Give "Sin confirmar" its own glyph (for example a dotted hollow ring or an ellipsis) and keep "?" only for the "Evidencia insuficiente" verdict. Write stage names instead of bare numbers in "comunes (Planificar, Crear código…)", and use lowercase v1/v2/v3 in the inspector tabs.
- Command: /impeccable clarify assessment/static/app.js

**[P2] Delivery cards are dense and repetitive. Each card is about 1,500px tall on desktop, and the 390px page is 8,062px. Each card has about 17 controls. Five equal-weight outlined buttons (Informe, Evidencia, TRX, Registro, Decisión humana) sit directly under Aprobar/Descartar. The conclusion is restated four times: reason text, "Siguiente paso", verdict strip and closing banner. Subgrid row alignment leaves about 300px of blank space in v1. The text uses 8 font weights, 127 bold nodes and mostly 13px type.**

- Why: The direction contract asks for a ledger compared row by row, but the comparison scrolls off after the first band. At the governance decision the reader faces 11 options, which is the Wall of Options pattern, and the decision buttons lose contrast against the artifact buttons. On mobile, comparing three stacked cards means about 5,000px of scrolling.
- Fix: Collapse the artifacts into one quiet "Artefactos: Informe · JSON · TRX · Log · Checkpoint" row of plain links placed after the decision, or into a single disclosure. Drop the in-card "Siguiente paso" where the closing banner already states it. Let the v1 governance and artifact rows collapse instead of reserving subgrid height. Reduce to 3 weights (400/600/750) and let labels use the muted color instead of bold.
- Command: /impeccable distill assessment/static/style.css

**[P2] Expected outcomes are hard-coded and shown before any evidence exists. The versionRoles constant renders card subtitles ("Código excluye cancelados · Prueba REN-001 presente", "Regresión funcional en cancelados · Prueba detecta fallo"), and the scope options ("Solo Versión 3 · Suite en verde sin evidencia REN-001") state the verdict before a run, on an unevaluated card or after a regression.**

- Why: Principle 1 is "Evidencia verificable antes que opinión". A certification console that labels the answer ahead of time looks scripted to an auditor. If v1 ever regresses, the card will show "Prueba REN-001 presente" next to an "Incumplido" badge.
- Fix: Before a run, show neutral identifiers only ("Versión 1 · carpeta v1/"). After a run, derive the subtitle from the report (deciding test and outcome). Rename the scope options to "Solo v1 / Solo v2 / Solo v3" and move the narrative roles into the help drawer as the demo scenario.
- Command: /impeccable clarify assessment/static/app.js

**[P2] Assistive-tech gaps in the evidence controls. A successful copy swaps only the focused button's aria-label; announce() is called only on the failure path, so a screen reader may say nothing. The copy buttons' accessible names ("Copiar hash de commit de v1", "Copiar huella anti-duplicados (WIQL) para v2") do not contain their visible text ("commit 14b2b829", "devsecops-fp-edf6e8b8a6d0"), which fails WCAG 2.5.3 Label in Name for voice-control users. The "Sin datos" pip in the help drawer is invisible (white fill, border rgba(0,0,0,0) on #f7faff).**

- Why: PRODUCT.md commits to full keyboard use, state changes announced, and states that do not rely on color alone. Copying the fingerprint is a key evidence step for QA and SecOps reviewers.
- Fix: Call announce(`Copiado: ${text}`) on success. Build the aria-label from the visible text ("commit 14b2b829, copiar hash de v1"). Give the help-drawer pip the same 1.5px border-control stroke that the corridor legend uses.
- Command: /impeccable harden assessment/static/app.js

#### Persona Red Flags

- **Alex (impatient power user)**: With "Solo brechas" on, ←/→ still steps through all 8 stations, including verified ones, and wraps 8 to 1; there is no "next gap" key. There is no shortcut to the governance decision: reaching v3's Aprobar means tabbing through about 30 controls per card, and the jump buttons ("Revisar acción de v2/v3") sit in the closing banner at the very bottom. Each D press replays a staggered re-entry animation of up to about 0.4s. Three run entry points (the global run plus "Evaluar vX" on each card) with a 4s timed arm for paid runs can surprise a fast double-clicker, although this one is safe by design.
- **Sam (screen reader / keyboard only)**: Positives verified live: a working skip link, a 3px focus ring in two tokens (blue on light, cyan on navy), logical tab order (masthead, then guide, verdict chips, form), focus returned on Esc from the inspector and help, polite live regions, every mobile target at least 44px, and no text-contrast failures in a text-only scan. Problems: copy success is silent; copy buttons fail Label in Name; the card stage summary "6 comunes (1, 2, 3, 5, 6, 7)" is a bare number list with no stage names; the "Sin datos" pip in the help drawer is invisible; the agent investigation is a single unstructured paragraph of 300+ words with no headings.
- **CISO in a live executive review (derived from PRODUCT.md Users)**: Reads the verdict strip in under 5s, which works. Then presses D for gaps and loses the 8 open SAST alerts (stage 3) and the 27.78% 5xx rate (stage 7). Reads "v1 queda certificada" next to "SecOps: 1 alta" and "revisa… antes de certificar". Notices the cards already said "Prueba REN-001 presente" and "Prueba detecta fallo" before any run, so the demo feels scripted. Meets WIQL, TRX and HITL in the cards with no inline definition. At presentation zoom each card is a long scroll, so the side-by-side contrast is lost after the first band. All three cards show the same "commit 14b2b829", so the commit cannot tell the deliveries apart; only the SHA-256 file counts (7/6/6) differ.

#### Minor Observations

- The help drawer's "Sin datos" pip renders invisible: background rgb(255,255,255), border 1.5px rgba(0,0,0,0) on a #f7faff drawer. The corridor legend's version uses a visible #5576a6 ring.
- "Huella anti-duplicados" is 16px regular, while the field label right below it ("Nota de auditoría…") is 13px bold. The governance block mixes two label systems.
- Inspector version tabs read "V1/V2/V3", and the inspector meta reads "Vista activa: V2"; everywhere else uses lowercase "v1".
- Wide shadows on the help drawer (-12px 0 32px) and the docked sheet (0 -8px 24px) go against the OWN-WORLD rule "cero sombras anchas".
- Typography: 8 computed weights (400/600/650/700/730/750/760/800), 24 text nodes at 11px, 267 at 13px. tabular-nums appears on only 12 selectors, although the contract asks for tabular numerals.
- The hub caption wraps as "Dictamen REN-001.v2 ·" / "HITL" at 1440px, leaving HITL orphaned on its own line.
- The inspector's "Respuesta en vX" column is mostly empty at desktop. In stage 5 the public ingress URL breaks across 4 lines in a 6-column grid.
- The status banner ("Mostrando 3 corridas previas en caché (0 tokens)…") repeats the verdict headline's "corridas en caché (0 tokens)" one band above.
- In the running state the card's previous evidence is cleared, leaving a nearly blank column with a thin bar beside two full cards. The provenance "Ejecutando ahora…" uses the green that means Verificado.
- On load with cached runs, the engine select silently switches to "Solo evidencia · 0 tokens". This is the safe default, but nothing announces it.
- Mobile: the masthead and sandbox strip take about 290px before the H1. The ecosystem pills scroll horizontally with the third pill clipped and a visible scrollbar.
- At 1440x900 only the heading "Matriz comparativa de entregas" shows at the fold. The contract asked for the matrix itself to start in the first viewport.
- Agent investigations are clearly separated (collapsed, at the bottom, labelled "Investigación Agente QA (MAF)") but carry no explicit statement that they do not decide the verdict. The QA text also contains a garbled agent sentence ("Fallaron otros tests vinculados pasaron correctamente").
- Done well and worth keeping: the docked sheet sets scroll-padding-block-end so focus is never hidden under it; the help drawer closes when focus leaves it; the reduced-motion handling in CSS and JS (opacity-only animateIn, auto scroll) is complete.

#### Cognitive Load

Moderate: 3 of 8 checklist items fail, and a fourth is borderline. Chunking fails because the corridor legend asks the reader to learn 6 stage states plus the \"1·2·3 = v1·v2·v3\" key, and each card lists 5 artifacts. Minimal choices fails at the decision points listed below. Working memory fails because of the version pip codes and the card summary \"6 comunes (1, 2, 3, 5, 6, 7) sobre la matriz\", which points to a different band. Hierarchy holds in the first viewport but flattens inside the cards (bold 13px everywhere). Items that pass: grouping into card bands and corridor lines, progressive disclosure (agents collapsed, inspector and help on demand, sandbox actions behind \"Gestionar :5080\"), and single focus in the first viewport, where the verdict strip clearly leads.

Decision points with more than 4 visible options:
- First desktop viewport: about 13 interactive targets (3 ecosystem links, Abrir portal, Gestionar, Guía, 3 verdict chips, 2 selects, Ejecutar, Solo brechas).
- Governance footer of the v2 and v3 cards: 11 (copy fingerprint, note field, Aprobar, Descartar, 5 artifact buttons, 2 agent disclosures).
- Card header: Evaluar vX, Iniciar vX and the SecOps flag (3, acceptable).
- Inspector toolbar: 6 (V1/V2/V3, Anterior, Siguiente, Cerrar).
- Help shortcut list: 7.

The 8 corridor stations are well chunked as 4 + hub + 4 and are acceptable. Intrinsic load (three deliveries × eight stages × two evidence sources) is high by nature. The extraneous load comes from duplicated conclusions and overloaded number codes.

#### Detector and Measured Checks (B)

- cramped-padding: <div> "sandbox-strip": children flush against bg on all sides (no inset). Category quality. The CLI reported line 0. The location was resolved by hand to index.html:65 (<div class="sandbox-strip">) and style.css:344-348 (.sandbox-strip { background navy-mid #0d2b59; border-block-start 1px; padding-block: 6px }).
- False positive: CLI cramped-padding on .sandbox-strip is partly a false positive. Horizontal inset: the static scan cannot resolve .frame { inline-size: min(1280px, calc(100% - 40px)); margin-inline: auto }. In the browser the visible text is inset 73px from the band edge at 1440 and 29px at 390. The second child .frame (the Reintentar/alert wrapper) is [hidden] with a 0x0 rect and probably triggered the 'flush on all sides' result. Vertical inset: this part is real. Padding is 6px plus a 1px top border, so the first text line ('Sujeto activo (v1) en 127.0.0.1:5080') sits 7px below the band edge, under the detector's 8px minimum. The band's children are 44px-tall controls with their own bordered fills, and this is a full-bleed toolbar band rather than a bordered card. Whether 6px is acceptable here is a judgment for Assessment A.
- False positive: Disabled buttons at 3.25:1 in the running state are exempt under WCAG 1.4.3 (inactive UI components). Opacity is 0.6 and the buttons are deliberately disabled during a run. The number is kept for reference.
- False positive: #shortcuts-toggle at 18x18 is not a target-size failure, because the wrapping label 'Atajos de una tecla activos' gives a 424x44 (1440) / 319x44 (390) hit area.
- False positive: During the Tab sweep the focused summary '8 etapas · 2 verificadas…' reported inView=false. This was a timing artifact of the measurement. With programmatic focus, the 44px summary sits at y=428-472 inside the 900px viewport, with a 3px solid ring. The page has no sticky or fixed elements that could cover a focused element.
- False positive: Mobile width caveat: at 390 the layout width (clientWidth) was 375, because headless Chromium draws a 15px classic scrollbar. Real iOS uses overlay scrollbars, so content would get the full 390px. Width numbers at 390 are measured at 375.
- Horizontal overflow at 1440x900: scrollWidth 1425 = clientWidth 1425, no page overflow. 0 non-fixed visible elements extend past the right edge.
- Horizontal overflow at 390x844: scrollWidth 375 = clientWidth 375 (15px classic scrollbar), no page overflow. Only the children of nav.ecosystem-nav extend past the viewport (a#nav-sec R=543), and that nav clips them with overflow-x:auto. Document height 8286px.
- Targets under 44x44 in the default view: 0 of 79 visible interactive elements at 1440 and 0 of 79 at 390.
- Targets under 44x44 in hidden panels: help drawer 1 of 2 (#shortcuts-toggle 18x18, but its label is 44px tall, so it passes). Stage inspector 0 of 7 at both sizes. Governance confirm buttons 195x44 and 89x44. Validation and confirm states were measured at both sizes.
- Text contrast across every visible text node, with alpha and ancestor backgrounds composited (opacity was only included in the running-state and panel passes): 364 nodes at 1440 and 346 at 390. 0 nodes below AA (4.5 normal / 3 large). Lowest: span.line-bullet 'CO' #f4f8ff on #1f5fc4 = 5.65:1 at 12px/800.
- Muted and secondary ink pairs: --ink-muted #435c82 on #ffffff = 6.79:1 (60 nodes, down to 11px; 10px .ver-num at 390); on canvas #f2f6fc = 6.26:1 (3 nodes, p.section-sub). --ink-secondary #1e3658 on white = 12.18 (59 nodes); on well #e8f0fb = 10.61; on tint #f7faff = 11.64; on error tint #fde8e8 = 10.38; on canvas = 11.23. --ink-on-navy-muted #c4dbfa on navy-deep #081c3a = 12.01 (masthead .brand-sub at 12px).
- Focus-visible: style.css contains no 'outline: none' or 'outline: 0' (grep returned rc=1). The global :focus-visible rule is 3px solid with 2px offset (style.css:227-235); on navy (masthead, corridor hub, matrix close) the ring is #7dd3fc. A Tab sweep covered 40 stops (21 unique elements, of 79 interactive). All 40 matched :focus-visible and showed a 3px outline; 0 had no ring. Ring contrast: #1d4ed8 on white 6.70, on canvas 6.18. #7dd3fc on #081c3a 10.18, on #0d2b59 8.36.
- Elements whose [hidden] is overridden by CSS: 0 of 13 [hidden] elements render at 1440 or 390. style.css:122-125 sets the global rule [hidden]{display:none !important}.
- Console errors from the page: 0 errors and 0 warnings across all reloads, both viewports, the running-state preview and the panel interactions. The session total of 2 errors are both from the CSP preflight probes.
- Reduced motion (CSS): every transition and animation declaration is inside @media (prefers-reduced-motion: no-preference) at style.css:2312-2466. The reduce block at 2468-2479 uses only opacity and colour: a static rail signal and a 200ms linear fade-in. Grep found no transition or animation declarations outside these blocks, apart from @keyframes.
- Reduced motion (JS): animateIn (app.js:291-297) uses opacity-only frames when reducedMotion.matches. Every scrollIntoView and scrollBy call (app.js:783, 791, 1432, 1468, 1557, 2088) switches behavior to 'auto' under reduce. Runtime check: with reducedMotion emulated as 'reduce' in the running-state preview, 0 animations were running. Without it, spin@#run-btn and dot-breathe@.status-dot ran infinitely.
- Smallest rendered font sizes at 390: 10px for 24 .ver-num nodes, 12px for 5 nodes, 12.04px for 8 code nodes, 13px for 258 nodes (the dominant body size), 14px for 32 nodes. At 1440 the minimum is 11px (.ver-num).
- Focus management in overlays: help drawer, stage inspector and governance confirm box each receive focus when opened. Escape or Cancelar returns focus to the control that opened them (verified at 1440 and 390).

#### Questions to Consider

- If REN-001 certifies exactly one rule, should the word "certificada" ever appear next to "SecOps: 1 alta" without a qualifier? And is an "Informativo" stage that says "revisa antes de certificar" really not a gap?
- Should the console tell the evaluator what each delivery is supposed to be before the evidence runs? What happens to trust in the tool the first time v1 regresses and its subtitle still says "Prueba REN-001 presente"?
- Is the matrix three 1,500px cards because comparison needs it, or because each report has that many fields? Could the corridor and inspector be the comparison, with each card reduced to a single evidence-and-decision ledger row?
- Should Aprobar en Azure Boards require a written justification too, since its write to a shared backlog is the less reversible of the two decisions?
