---
target: assessment/static/index.html
total_score: 31
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:/Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html"
target_fingerprint: "sha256:e0a5ba2d14ca919d7c77daaff8a4f574071431f134aa5b7b6e4f0b6994124190"
target_path: /Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html
timestamp: 2026-11-27T13-49-06Z
slug: assessment-static-index-html
---
Method: dual-agent (A: a065571bf806852bc · B: a1adf1e60b8a8ba47)

#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Feedback is broad: toned status banner, live regions, live-vs-cache provenance with timestamps, an elapsed clock and hub line during runs, a countdown on decisions and copy confirmation. The gap is that a multi-minute agent run shows only an indeterminate bar and the clock. There is no phase progress (compile, xUnit, SHA-256, QA/SecOps agents, policy), and a delivery with no cached run has its card body cleared while it runs. |
| 2 | Match Between System and Real World | 3 | Mostly natural technical Spanish: test names are humanized and acronyms carry definitions. Some raw or internal text leaks through: the raw enum 'CUMPLIDO' and 'N/A' in the stage-8 v1 data, '1 observación(es) de postura', 'Assert.Empty(datos.Avisos)' in v2's headline reason, internal terms such as 'banda superior' and 'Núcleo determinista', and the self-contradicting tag 'Informativo · por revisar' on a 27.78 % 5xx rate. |
| 3 | User Control and Freedom | 3 | Esc closes layers one at a time and returns focus. Governance has Cancel as the default focus plus a 5 s 'Deshacer', and Esc×2 stops a run. However, syncHash uses history.replaceState, so browser Back leaves the console instead of closing the inspector. A discard becomes permanent once the grace window ends (by design). |
| 4 | Consistency and Standards | 3 | There is one state vocabulary, with glyphs. The inspector's 'Mismo resultado en v1, v2 y v3' compares only estado/resumen, while the matrix also compares datos. So stage 5 is 'the same' in the inspector but 'different' in the matrix, and the inspector drops v1's distinct note about uncommitted local changes. Two smaller mismatches: v3 stage 4 reads 'Sin confirmar' (dots glyph) while its verdict reads 'Evidencia insuficiente' ('?' glyph), and the inspector shows stage 7 as a grey 'Informativo' while the matrix shows an amber 'Informativo · sin línea base'. |
| 5 | Error Prevention | 3 | The HITL path is exemplary: the confirm text states the consequence and the fingerprint, Cancel gets focus, there is a 5 s 'Deshacer', and discarding requires a note with an inline aria-invalid error. Agent runs need a second press. But in the default 0-token mode, 'Ejecutar evaluación' and each card's 'Evaluar vN · 0 tokens' start a real dotnet build and test on one click. The card buttons sit at the very top of every card, right beside the provenance chip. |
| 6 | Recognition Rather Than Recall | 3 | The legend, inline kbd hints and footer shortcut list help. But telling 'Sin confirmar' (amber dotted border, dots glyph) from 'Atención requerida' (orange dashed border, '!' glyph) in the matrix means remembering the corridor legend about 600px above. The summary '5 comunes en la banda superior' also asks the reader to remember another region. |
| 7 | Flexibility and Efficiency of Use | 4 | Strong accelerators: R, D, 1–8, ←/→, V, ? and Esc, with a persisted on/off toggle; shareable #etapa/#version/#filtro deep links; per-delivery runs; and jump buttons in the matrix-close bar. One nit: ←/→ are captured page-wide whenever the inspector is open, even when focus is on a matrix row. |
| 8 | Aesthetic and Minimalist Design | 3 | The navy and porcelain system is restrained and the first viewport is clean. The matrix is noisy: about 11 amber or orange blocks across the three cards and the shared band (including the v1 'Verificado' card); stage summaries run to 2–3 lines in bold; an identical commit chip appears three times; the status banner repeats the headline's cache wording; and subgrid alignment leaves large empty areas (v1 verdict band, v3 proof band). |
| 9 | Help Users Recognize, Diagnose, and Recover from Errors | 3 | Scored from source only, because no error state could be triggered safely. The copy is specific (for example 'confirma que python -m assessment.ui sigue en ejecución'), retries are inline, the note and prior evidence are kept, and an agent failure offers a 0-token retry, which would justify a 4. But backend data.error strings are shown unmodified in the status bar, card alerts and the governance error box, and their language and wording are unverified. |
| 10 | Help and Documentation | 3 | There is a task-organized help drawer, inline acronym definitions, a governance question per stage and 'Siguiente paso recomendado'. But the definitions exist only as abbr title tooltips, which mouse users can see but keyboard and touch users cannot. The key 'Sin confirmar' vs 'Evidencia insuficiente' distinction is explained only in the drawer, not on the v3 card where the confusion arises. |
| **Total** | | **31/40** | **Good** |

#### Anti-Patterns Verdict

Built for this product, not a generic template. The transit corridor is authored for this domain: a DevSec line and a CloudOps line meet at a "Núcleo determinista" hub, and each station shows per-delivery pips that carry both shape and colour. The domain detail runs through the rest of the page: verdict chips that name the deciding xUnit test and its outcome, the SHA-256 signed-file count, the WIQL fingerprint with a copy control, and the HITL confirm with a 5 s undo window. None of this could be lifted into another product unchanged. The generic part is the matrix card shell: white 14px-radius cards, pill badges and 1px state-coloured borders, which any SaaS dashboard could use.

#### Overall Impression

Arrival is confident. The navy institutional masthead, a green dot with 'Sujeto activo (v1)', and the verdict strip deliver the peak within 5 seconds, with each chip citing the deciding test.

The first valley comes on scrolling into the matrix. Amber appears everywhere: the certified v1 card carries an amber 'no se puede confirmar que sea el mismo código', and the shared band labels a 27.78 % 5xx rate as 'Informativo'. Doubt replaces the clarity of the strip, and an executive may now distrust the green chip they just read.

The inspector restores a sense of control (smooth inline detail, the stage's governance question, side-by-side comparison) until a careful reader sees 'Mismo resultado' sitting above notes that differ.

The high-stakes moment, approving to Azure Boards, is handled very well. The consequence and fingerprint are spelled out, Cancel is the safe default, and a 5 s 'Deshacer' follows confirmation, so the user feels protected exactly when stakes peak.

A second, smaller valley appears during a live agent run: an indeterminate bar and a clock for minutes, with no sense of which phase is running.

The ending is strong. The navy matrix-close bar ('v1 queda certificada… decidir las 2 acciones') gives closure and a next step, so the peak-end rule works in the page's favour, provided the matrix noise doesn't spoil the middle.

#### What's Working

- The verdict strip answers the 5-second question. Each chip names the deciding evidence (for example 'v2 × Incumplido · Prueba «cancelado no genera aviso»: fallida'), and the headline counts gaps and pending human actions and states whether results are cached or live. The navy matrix-close bar ends the page well: 'v1 queda certificada… decidir las 2 acciones' with 'Revisar acción de v2/v3' jump buttons. This is a good peak and a good ending.
- Governance is designed for deliberate decisions. Validation is inline, specific and focused, with aria-invalid on the note. The confirm text explains the idempotent WIQL behaviour with the actual fingerprint. Focus lands on Cancel so a stray Enter cannot write to Boards, and Esc inside the confirm box cancels. A 5 s 'Deshacer' window follows confirmation. Agent runs need a second press, and the engine defaults to 0 tokens when a cached run exists.
- The corridor and inspector interactions are polished and accessible. The inspector opens inline from a station or docks as a bottom sheet from a card row, and on both 1440 and 390 widths the originating row stays visible above the sheet. It responds to ←/→, V, 1–8 and Esc, and wrap-around is announced. The version buttons keep focus and aria-pressed. Focus returns to its origin on close, and each view gets a shareable hash. Accessibility basics are solid: a visible 3px focus ring on every Tab stop (light blue on navy), a skip link, polite live regions, every motion gated by prefers-reduced-motion, forced-colors rules, no target under 44px at 390px, and text contrast of 6.3:1 or better throughout.

#### Priority Issues

**[P1] Amber and orange carry four different meanings, so the matrix loses its v1/v2/v3 contrast. They encode the delivery verdict 'Evidencia insuficiente', the stage state 'Sin confirmar' (dotted border, dots glyph), the stage state 'Atención requerida' (dashed border, '!' glyph), and the bold notes on 'Informativo · por revisar / sin línea base'. At 1440 there are about 11 amber blocks across the shared band and the three cards. The v1 'Verificado' card itself shows an amber dotted block: 'Desplegada en Azure: v1, pero el repositorio tiene cambios locales… no se puede confirmar que sea el mismo código'.**

- Why: Product Principle 2 says a leader should see in one glance why v1 passes, v2 fails and v3 is held. In a live executive demo, an amber caveat on the certified delivery invites the question 'is v1 certified or not?'. Meanwhile v3's amber verdict blends into ordinary caveats, and the only cue separating a blocker from a footnote is the dash pattern of a border or a 10–12px glyph.
- Fix: Keep amber for the 'insufficient or unconfirmed' family only: the verdict 'Evidencia insuficiente' and the stage state 'Sin confirmar'. Move 'Atención requerida' (a pending human decision) to the institutional blue action colour, labelled 'Decisión pendiente', so it reads as workflow rather than evidence quality. Show informative notes such as SAST alerts, no 5xx baseline or local changes in neutral ink with a small marker, not bold amber. When the same caveat applies to all three deliveries (the stage-5 deployment mismatch), state it once in the shared band rather than in every card.
- Command: /impeccable colorize

**[P2] The first viewport misses the direction contract, and the matrix is wordy. At 1440×900 only the 'Matriz comparativa de entregas' heading is visible at the bottom edge, with no matrix content, although the surface brief requires the matrix to start in the first viewport. Inside the matrix, stage summaries are 2–3 bold lines, for example '8 etapas · 1 incumplida · 1 sin confirmar · 1 con atención requerida · 5 comunes en la banda superior · filtro «Solo brechas»: 0 ocultas'. The same commit chip (14b2b829) with a copy button appears three times. The status banner ('Mostrando la última corrida guardada…') and the mode caption ('Elegido porque ya hay corridas guardadas…') both repeat the headline's 'corridas en caché (0 tokens)'.**

- Why: The deck repeats one fact three times, and the corridor intro plus its six-item legend take about 120px before any matrix content appears. Readers parse run-on counts instead of scanning, and the most decision-relevant region begins below the fold.
- Fix: Hide the status-banner text when it restates the headline, and fold the mode caption into the select's description. Move the corridor legend into a compact one-line key or the help drawer. Replace the summary sentences with a pip row plus a single count ('3 brechas · 5 comunes'). Show the shared commit once in the shared band header. These changes recover about 150–200px, enough to show the shared band in the first viewport.
- Command: /impeccable distill

**[P2] The inspector states that results are the same when the evidence differs. For stage 5 it says 'Mismo resultado en v1, v2 y v3' because it compares only estado|resumen. computeSharedStages in the matrix also compares datos, so the matrix lists stage 5 separately in each card. The per-version notes differ (v1: 'cambios locales sin publicar'; v2 and v3: 'Desplegada en Azure: v1, no esta entrega'), but the 'same' block drops them and shows a plain grey badge.**

- Why: The product's claim is deterministic traceability. A summary that says 'same' under a note showing the opposite undermines trust in every other summary on the page, especially for the QA and SecOps reviewers who will cross-check it.
- Fix: Have openStageInspector use the same signature as computeSharedStages (estado|resumen|datos, plus stageNote). If notes or data differ, render the three-column comparison instead. Show the same flagged tag in the inspector as in the matrix ('Informativo · sin línea base').
- Command: /impeccable harden

**[P2] One click starts a real build. In the 0-token default, 'Ejecutar evaluación' and each card's 'Evaluar vN · 0 tokens' start a dotnet build and xUnit run immediately, with no confirmation (confirmPaidRun returns true when mode is not 'agente'). Each card button sits at the very top of the card, next to the provenance chip and above the verdict, which is where an executive's pointer lands when reading. Separately, the run provides no phase progress beyond an indeterminate bar and an elapsed clock.**

- Why: A misclick replaces 'Corrida previa en caché' with a live run, locks that card's governance panel (inert) for the duration, and can turn a stable demo into a multi-minute wait. For a reader rather than an operator, the button is both prominent and irrelevant.
- Fix: Move per-delivery 'Evaluar' into the card footer or an overflow menu next to Artefactos. When a cached verdict would be replaced, require a second press, reusing the arm() pattern already used for Detener :5080 ('Reemplazar corrida de 26 nov, 14:40? Pulsa otra vez'). During a run, show a 4–5 step phase list in the busy card's verdict band.
- Command: /impeccable harden

**[P2] Several gaps for screen-reader, keyboard and touch users. (1) The Boards confirmation moves focus to 'Cancelar', whose accessible name gives no context. The consequence text is attached only as the description of 'Confirmar envío a Boards', and the group label is the generic 'Confirmación de decisión de gobernanza', so the question itself is never read. (2) Station numbers are aria-hidden, so buttons announce 'Integrar y probar (…)' even though the help text says 'pulsa 1–8'. (3) Acronym definitions (WIQL, TRX, SHA-256, CSPM, KQL, SAST) exist only as abbr title tooltips, which keyboard and touch users cannot reach. (4) Pressing Anterior from stage 1 to wrap to stage 8 announces 'Vuelta al inicio del recorrido', which is the wrong direction.**

- Why: PRODUCT.md commits to WCAG 2.1 AA and full keyboard operation. The most consequential action on the page, writing to Azure Boards, is the one whose prompt a screen-reader user never hears.
- Fix: Give the confirm box role=alertdialog-style labelling via aria-labelledby on the prompt, and add aria-describedby pointing at the prompt to 'Cancelar' as well. Include 'Etapa N' in each station's accessible name. Render acronym definitions in a focusable disclosure, or let the help drawer's glossary be reached from each term. Use 'Vuelta al final del recorrido' when wrapping backward.
- Command: /impeccable audit

#### Persona Red Flags

- **Alex, impatient power user (QA lead)**: Shortcuts cover reading (1–8, ←/→, V, D, ?) but not acting. There is no key to jump to the next pending decision, and each of the two pending actions needs a full pass: scroll, focus the note, Aprobar, Confirmar, then wait out the 5 s grace. While the inspector is open, ←/→ are taken page-wide, so arrows stop working for anything else even when focus is on a matrix row. In docked mode, stepping with ←/→ leaves the original chip highlighted ('4 · Integrar y probar' stays .is-inspecting while the sheet shows stage 5), and Esc returns focus to that stale chip. Keyboard stepping keeps the previously chosen version: from v1 on stage 2, pressing 8 shows v1 'Verificado' instead of the worst version, so the 'open on the problem' heuristic applies only to the first open.
- **Sam, screen-reader and keyboard user**: Positives: the Tab order is logical (skip link, ecosystem links, sandbox, guide, 3 verdict chips, selects, run, filter, 8 stations); all 21 stops checked show a 3px focus ring; status and copy events are announced. Red flags: the Boards confirmation lands on 'Cancelar' with no context about what is being confirmed. Station buttons omit their number while the help says 'pulsa 1–8'. Acronym definitions are title-only. The inspector's version selector is three aria-pressed buttons named 'v1/v2/v3' with no state in their names; the state is announced separately via the live region. The backward-wrap announcement is wrong ('Vuelta al inicio' when going from 1 to 8).
- **Jordan, first-time executive in a live demo**: The first 5 seconds go well because the verdict strip is clear. Confusion starts in the matrix. The certified v1 card carries a bold amber warning ('no se puede confirmar que sea el mismo código'). v3's verdict is 'Evidencia insuficiente' while its stage 4 says 'Sin confirmar'; the help drawer explains the difference, but nothing near the card does. The shared band labels a 27.78 % 5xx error rate as 'Informativo'. Jargon without inline help includes 'Núcleo determinista', 'banda superior', 'Huella anti-duplicados (WIQL)' and 'Assert.Empty(datos.Avisos)' in v2's main reason. The most prominent button on each card is 'Evaluar vN · 0 tokens', which looks like the obvious next step but starts a real build.

#### Minor Observations

- The inspector shows the raw enum 'CUMPLIDO' and 'N/A' in v1's stage-8 data ('Estado gobernanza', 'Clave idempotencia'), despite the code comment 'backend enums never reach the screen'. ENUM_TEXT has no entry for CUMPLIDO.
- '1 observación(es) de postura' leaks a backend pluralization placeholder into the shared band.
- The matrix subtitle 'Las tres entregas lado a lado' is false at 390px, where the cards stack: v1 1208px, v2 1643px, v3 1535px tall, with v3's governance about 6,500px down a 7,432px page.
- On mobile, the masthead plus sandbox strip take 243px (29 %) of the first viewport, and the ecosystem pills scroll horizontally behind a visible scrollbar. Opening 'Gestionar :5080' pushes the verdict strip below the fold.
- The docked sheet and the mobile inline inspector show a double frame at the top (focus outline plus inner border), and the outline cuts across the text behind the sheet.
- On mobile, tapping a DevSec station (1–4) opens the inspector below the CloudOps line, about 450px from the tapped station.
- In the inspector, the question block is tinted while the answer block ('Respuesta en v2') is plain text with no state badge, so the less important element carries more visual weight.
- The station 'ver-num' labels are 11px; most card body text is 13px, which is small for presentation-zoom demos.
- The help drawer is a non-modal 480px panel with no scrim that closes on focus-out. It covers the ecosystem pills and needs about 1,480px of scrolling across 7 sections. The code token 'devsecops-fp-…' is truncated.
- 'Solo brechas' removes only 2 shared stages and the verified chips. The proof, verdict and governance bands stay unchanged, so the filter's visible effect is modest and its note ('el corredor muestra las 8 etapas') applies to a different region.
- Approving to Boards requires no audit note, while discarding does. This is an asymmetric audit trail for a write to an external system.
- The status banner's warn-tone message for the Esc×2 arm restores the previous message after 3 s, but an announcement queued in between would be overwritten (source reading).
- A full-page capture at 390px timed out in DevTools, so mobile coverage comes from viewport captures and layout measurements: no horizontal overflow, no target under 44px.

#### Cognitive Load

Moderate: 3 of the 8 checklist items fail.

Failures:
- Chunking: the corridor legend has 6 items, and the stage vocabulary adds the 'por revisar' and 'sin línea base' suffixes and 3 delivery verdicts. That makes about 11 codes to decode, carried by colour, border dash pattern and 10–12px glyphs.
- Minimal choices: several decision points exceed 4 options (listed below).
- Working memory: 'Sin confirmar' (dotted) vs 'Atención requerida' (dashed) has to be recalled from a legend about 600px above the matrix; '5 comunes en la banda superior' points to another region; the 'Sin confirmar' vs 'Evidencia insuficiente' distinction is explained only in the drawer.

Passes: grouping (cards, bands, DevSec and CloudOps lines of 4), visual hierarchy in the first viewport (the verdict strip dominates), one thing at a time (the inspector shows one stage; the confirm step shows one decision), and progressive disclosure (details, inspector, drawer, sandbox toggle).

Decision points with more than 4 visible options:
- Command deck: 8 controls (3 verdict chips, 2 selects, run, filter, guide).
- Corridor: 8 station buttons carrying 24 version pips, plus the 6-item legend.
- Inspector toolbar: 6 controls (v1, v2, v3, Anterior, Siguiente, Cerrar).
- Expanded 'Gestionar :5080': 6 controls (v1 active, Iniciar v2, Iniciar v3, Detener, Abrir portal, toggle).
- Masthead: 5 links or buttons.
- Lower half of the v2 and v3 cards: about 11 controls (copy fingerprint, note, Aprobar, Descartar, 5 artifact links, 2 agent disclosures).

Intrinsic load is high by nature (3 deliveries × 8 stages × 5 states). The extraneous load comes mostly from the overloaded amber family and the run-on summaries, not from the layout.

#### Detector and Measured Checks (B)

- cramped-padding (Cramped padding, category: quality): <div> "sandbox-strip": children flush against bg on all sides (no inset)
- False positive: cramped-padding on .sandbox-strip is a PARTIAL false positive. The claim that children sit flush on all sides is wrong in the rendered page. The strip has padding 6px 0 and its child .frame.sandbox-bar is inset by the page frame: 73px left and right at 1440, 12px left and right at 390. The static scan cannot see that .frame inset. The rendered-URL detector scan (impeccable detect --json http://127.0.0.1:8051/) also returned exit 0 with 0 findings. The real, minor residual is vertical: the strip is a visible boundary (bg rgb(13,43,89) = #0d2b59 on the masthead rgb(8,28,58) = #081c3a, plus a 1px solid top border), and its content sits 7px from the top and 6px from the bottom at both widths. That is just under the rule's 8px floor. Strip height is 57px at 1440 and 89px at 390.
- False positive: Horizontal scroller nav.ecosystem-nav at 390 (scrollWidth 544 vs clientWidth 363, overflow-x:auto, scrollbar-width:thin) is an intentional component scroller, not page overflow. The page itself does not overflow: documentElement.scrollWidth 375 == clientWidth 375. The thin bar visible under it in the screenshot is headed desktop Chromium's scrollbar. On iOS the only scroll cue would be the clipped third pill ('CodeQL y Dependabot'), since there is no mask-image and no scroll-snap. This is a design-review question, not a defect.
- False positive: The 390 viewport measured 375px of content width because headed Chromium on macOS draws a classic 15px scrollbar. It is not a layout bug.
- False positive: Disabled 'Evaluar v1/v2/v3 · 0 tokens' buttons in the previewed running state use opacity 0.6. The effective color rgb(115,144,191) on white measures 3.25:1. WCAG 1.4.3 exempts inactive controls, so this is not a contrast failure.
- False positive: aria-busy stayed 'false' on #results during the console running-state preview. That is an artifact of the preview: the snippet bypasses the real run path, which sets aria-busy=true at app.js:1980 and false at app.js:2100.
- False positive: The sr-only spans '(se abre en una nueva pestaña)' inside the masthead links were included in the contrast sample but are not visible text (1px clip). Ignore them for visual contrast.
- False positive: The 3 console errors seen during the session were all produced by my own CSP injection preflight (inline script, data: script, localhost:8400/detect.js). The page produced 0 errors and 0 warnings on clean loads at 1440 and 390, and after the governance interactions.
- CLI: impeccable detect --json assessment/static/index.html from cwd /Users/johnbenjamincastrosanabria/Developer/AppContratos returned exit 2 with 1 finding (cramped-padding, warning, line 0, .sandbox-strip). Supplementary rendered-URL scan: impeccable detect --json http://127.0.0.1:8051/ returned exit 0 with 0 findings. It is reported separately and not counted in cli_count.
- Response header CSP (curl GET): default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'. There is no meta CSP, so it cannot be stripped from the DOM.
- Horizontal overflow at 1440x900: documentElement.scrollWidth 1425 == clientWidth 1425 (15px scrollbar). 0 visible elements extend past the right edge.
- Horizontal overflow at 390x844: documentElement and body scrollWidth 375 == clientWidth 375. style.css has no overflow hidden/clip on html, body or any page wrapper (the only two overflow:hidden rules are .sr-only at line 207 and the inspector button sr spans at line 2749), so the equality is valid. The only internal scroller is nav.ecosystem-nav (544 vs 363, intentional). The per-element offender pass at 390 timed out once; the equality check plus the absence of root clipping stands in for it.
- Touch targets at 1440: 78 visible interactive elements, 0 under 44x44, 0 under 24x24. At 390: 78 visible, 0 under 44x44, 0 under 24x24. In the previewed running state at 390: 61 visible, 0 under 44x44. Governance confirm step: 'Confirmar envío a Boards' 192x44, 'Cancelar' 88x44.
- Text contrast at 1440 (58 unique fg/bg/size combos walked over every visible text node, colors normalized via canvas, alpha composited on ancestors, 0 gradient/image backgrounds): 0 failures. Lowest ratios: CO line-bullet #f4f8ff on #1f5fc4 = 5.65 (12px/750); --ink-muted #435c82 on --surface-canvas #f2f6fc = 6.26 (p.section-sub 14px, p.shared-stages-sub 13px); #435c82 on white = 6.79 (p.mode-caption 13px, span.ver-num 11px/750, p.version-role 13px/600); v3 verdict #664005 on #fef2cc = 8.17; v2 verdict #7f1d1d on #fde8e8 = 8.53; primary button #f4f8ff on #154694 = 8.44. Token checks: --ink-on-navy-muted #c4dbfa on #081c3a = 12.01; #435c82 on --surface-well #e8f0fb = 5.91.
- Text contrast at 390: 75 unique combos, 0 not computable, 0 failures. Lowest: shared-stages-sub 6.26, then mode-caption, section-sub, ver-num and version-role at 6.79.
- No visible text has ancestor opacity below 1 in the idle state. Text under 12px: only span.ver-num at 11px (24 instances), at contrast 6.79.
- Focus-visible at 1440: 90 real Tab presses (no Enter/Space/R). Every stop matched :focus-visible and every stop had an outline. Outline variants: 78 stops with 3px solid rgb(29,78,216) and 12 masthead stops with 3px solid rgb(125,211,252). Computed ring contrast: #1d4ed8 vs white 6.70, vs #f2f6fc 6.18, vs #e8f0fb 5.84; #7dd3fc vs #081c3a 10.18, vs #0d2b59 8.36. All are above 3:1. The first stop is a skip link 'Saltar al dictamen y los controles'.
- Focus-visible at 390: 80 Tab presses gave 79 real stops. 0 without a ring, 0 with :focus-visible false, 0 obscured by sticky or fixed elements (elementFromPoint test), 0 left out of view.
- [hidden] overrides: 14 [hidden] elements at both 1440 and 390, 0 with a computed display other than none. Base rule style.css:123 is [hidden]{display:none !important}.
- Console on clean load: 0 errors and 0 warnings at 1440, at 390, and after the governance interactions.
- prefers-reduced-motion, static: every animation and transition declaration in style.css sits inside @media (prefers-reduced-motion: no-preference) (lines 2335-2488). The reduce block (2491-2502) only swaps in a 200ms linear opacity fade-in on .station-num and .badge and makes the rail signal a solid color. style.css has no @layer, @supports or @container. JS animateIn (app.js:299) switches to opacity-only frames under reducedMotion. All smooth scrollIntoView/scrollBy calls (app.js:824, 832, 1514, 1552) fall back to 'auto' under reduce. app.js sets no style.transition or style.animation. A CSSOM walk found 0 motion rules outside a reduced-motion media query.
- prefers-reduced-motion, runtime, discriminating test in the running-state preview at 1440: under no-preference, document.getAnimations() = 77, of which 6 are infinite (spin on .btn-primary, dot-breathe on .status-dot, rail-signal on .station-list x2, hub-turn on the hub svg, track-run on .card-band). Under emulated reduce: 0 animations, 0 infinite. The idle-state check under reduce (also 0) does not discriminate, because nothing animates at idle.
- Governance (safe path only): 'Aprobar en Azure Boards' opens a role=group confirm box, and focus defaults to 'Cancelar' (a stray Enter cancels). 'Cancelar' closes the box and returns focus to 'Aprobar en Azure Boards'. 'Descartar' with an empty note shows a role=alert error 'Escribe un motivo en el campo de nota antes de descartar permanentemente esta brecha.' (#7f1d1d on #fde8e8 = 8.53:1), focuses the input with aria-invalid=true and aria-describedby=gov-error-v2, and opens no confirm box. The confirm prompt text shows the internal idempotency fingerprint (e.g. 'devsecops-fp-edf6e8b8a6d0').
- Running-state preview (console snippet, 390): status uses #status role=status aria-live=polite, and #announcer (sr-only, aria-live=polite) exists. Card eval buttons are disabled at opacity 0.6 (inactive, exempt).
- Screenshots (gitignored directory): /Users/johnbenjamincastrosanabria/Developer/AppContratos/.playwright-mcp/critB-desk-1440.png, /Users/johnbenjamincastrosanabria/Developer/AppContratos/.playwright-mcp/critB-mobile-390.png, /Users/johnbenjamincastrosanabria/Developer/AppContratos/.playwright-mcp/critB-gov-confirm.png.
- Safety: never clicked Ejecutar evaluación, Evaluar v1/v2/v3, Reintentar, Iniciar, Detener :5080, Confirmar envío a Boards or Confirmar descarte, and never pressed R. Only Aprobar, Descartar (empty-note validation) and Cancelar were clicked. Each page was reloaded after the preview and the interactions. No project file was edited: git status shows only the pre-existing modifications.

#### Questions to Consider

- If the verdict is decided by one stage (4, the linked xUnit test), why does the page give more space to the 8-station corridor, where most states are common or informative, than to the deciding evidence?
- Is 'Atención requerida' on stage 8 a property of the evidence or of the workflow? If it only means 'a human must decide', should it be the governance panel's own state instead of a fourth amber stage state?
- What would the matrix look like if its default were 'Solo diferencias' rather than everything, with 'Solo brechas' as the second filter? Would the shared band then be the matrix's first row?
- Is the console for the QA lead who operates it or the executive who reads it? Three 'Evaluar vN' buttons, three commit copy buttons and five artifact links per card suggest the operator's tools are crowding the reader's view.
