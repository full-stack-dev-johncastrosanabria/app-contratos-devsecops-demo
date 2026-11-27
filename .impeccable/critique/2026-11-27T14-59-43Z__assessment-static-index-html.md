---
target: assessment/static/index.html
total_score: 34
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:/Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html"
target_fingerprint: "sha256:e73cd2e17f90c38d0b282c1018581afdbf8055d40e9dfa3d51ae190e1a3bc33a"
target_path: /Users/johnbenjamincastrosanabria/Developer/AppContratos/assessment/static/index.html
timestamp: 2026-11-27T14-59-43Z
slug: assessment-static-index-html
---
Method: dual-agent (A: ad95f77c6d016714b · B: a11b7f09515004076) · round R8 on the ledger redesign, batch 8 (branch rediseno/libro-mayor)

#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Minor: a live run shows an elapsed clock and a per-column progress bar, but not the current phase. The chip lists «compilación, xUnit y agentes» all at once. The held column is greyscaled, so v2's red «Incumplido» reads grey mid-run; the glyphs survive. |
| 2 | Match System / Real World | 3 | Out-of-scope signals borrow REN-001 state words, so severity reads inverted to a CISO. Stage 3 (8 open CodeQL alerts; the SecOps agent rates one py/redos alert «Severidad alta») and stage 7 (27.78 % 5xx) are «Informativo». Stage 6 (one posture observation) is «Atención requerida». English also leaks through: «Estado en Boards: New», «PR #1 (merged)», «18 req». |
| 3 | User Control and Freedom | 3 | Strong confirm, Esc, Deshacer and Esc×2 paths. Gaps: the inspector toolbar (v1/v2/v3, Anterior, Siguiente, Cerrar) scrolls out of the 450px sheet when the content scrolls. The browser Back button never steps back through inspected stages because the hash is written with history.replaceState. |
| 4 | Consistency and Standards | 3 | The same amber outcome has two names on the deciding row. v3's header says «Evidencia insuficiente» while its «Decide REN-001» cell says «Sin confirmar», and the guide needs a paragraph to explain why. Blue does quadruple duty: brand chrome, primary action, «Atención requerida» and «Informativo · por revisar». «Entrega» and «versión» are used interchangeably. |
| 5 | Error Prevention | 4 | Minor: approving in Azure Boards is allowed with an empty audit note (only discarding requires one). Everything else is guarded: paid runs need a second press, R only moves focus, the engine switches to 0 tokens when a cache exists, approve and discard need a confirm plus a 5 s Deshacer, and replacing the sandbox needs a second click. |
| 6 | Recognition Rather Than Recall | 3 | The dossier shows one delivery at a time, so comparing the two pending decisions (v2 and v3) means switching tabs and remembering the other. With the sheet open, only about 3 stage rows stay visible. The «· por revisar» and «· sin línea base» qualifiers can only be decoded from the help drawer. |
| 7 | Flexibility and Efficiency | 4 | Minor: V cycles versions forward only, and no key jumps from the inspected stage to that delivery's decision. The rest is excellent: R/D/1–8/←→/V/?/Esc with an off switch, ←/→ skipping clean stages under «Solo brechas», hash deep links (#etapa=4&version=v2), arrow-key tablist and copy buttons. |
| 8 | Aesthetic and Minimalist Design | 3 | Cache provenance is stated five times: the mode caption, the status banner, the ledger headline, each column header and the dossier chip. About 20 lines of copy and 10 controls come before the first stage row. Cells carry truncated technical strings («ca-appcontratos · revisión ca-appcontratos-…»). Nested rounded cards contradict the page's own direction contract. |
| 9 | Error Recovery | 4 | Judged mostly from code; the discard validation was exercised live. Errors keep the last good run on screen, offer a 0-token retry after an agent failure, keep the note on a governance retry, and put a manual-copy field next to the button when the clipboard is blocked. Minor: the raw server error text is interpolated in parentheses inside the Spanish message. |
| 10 | Help and Documentation | 3 | The guide is task-ordered and contextual (abbr tooltips, a governance question per stage, a legend, inline key hints). But it runs to about 1,560px with no search, has no dialog or landmark role, and closes silently when focus leaves it after two Tab stops. Its state section needs six bullets and «(en azul)» caveats, which is a symptom of the taxonomy problem. |
| | **Total** | **34/40** | |

#### Anti-Patterns Verdict

Mostly authored for this product, wrapped in generic chrome. The signature pieces could not belong to any other product. The stage × delivery ledger runs the DevSecOps transit line down the first column. Its station rings take the worst state and carry it in both colour and shape (solid, dashed, dotted). The DS/CO line bullets, the «Núcleo determinista» interchange row between stages 4 and 5, the «Decide REN-001» and «Contexto · fuera de REN-001» scope tags, the shared cells marked «Igual en v1, v2 y v3» and the closing «Decisión humana» row that jumps into the right dossier with the note field focused are all specific to REN-001 certification. Separating the deterministic proof from the MAF agent investigation, and showing the WIQL fingerprint as a copyable control, are also product-specific.

The chrome around that core could ship in any SaaS admin panel unchanged: a two-band navy masthead with outline pill links, rounded white cards on an ice canvas, a select / select / primary-button form row, green/red/amber pill badges, a tabbed dossier card and the system sans stack with no typographic signature.

The build also drifts from its own direction contract. The THESIS rejects nested cards, yet bordered 10px-radius ledger cells (stages 3 and 5–8) sit inside the bordered 14px-radius matrix card, and bordered compare boxes sit inside the inspector sheet. The STORY promises C# code and CLI output as deterministic proof. The UI shows only a file path («tests/Contratos.Tests/RenovacionesTests.cs:20») and links to the raw TRX and log.

The biggest missed opportunity is v2's failing assertion (Assert.Empty(datos.Avisos) with one aviso generated). It is the most persuasive fact in the product, and it appears only as a sentence in the dossier instead of being the visual centrepiece.

#### Overall Impression

The emotional arc is a confident open, a mid-matrix dip and a strong close at the decision.

- **Arrival: confidence.** The institutional navy masthead and the green/red/amber verdict triplet, each with its deciding test outcome, are readable within the first viewport. The pinned header keeps them visible on scroll. This is the first peak.
- **First valley: doubt in the middle of the matrix.**
  - The «Decide REN-001» row says «4 pruebas ejecutadas en TRX» for both the pass and the fail.
  - v3 turns into «Sin confirmar».
  - A CISO sees 8 SAST alerts and a 27.78 % 5xx rate labelled «Informativo» and starts to wonder whether the tool downplays security.
- **The inspector: relief.** The «Pregunta de gobierno / Respuesta en vN» framing restores it, but the half-height sheet makes the matrix feel lost.
- **The high-stakes moment: well cushioned.** The fingerprint is shown, the confirm text names the consequence, focus lands on «Cancelar», then a 5-second «Deshacer». This is the second peak.
- **The end: positive.** The flow closes on «Tarea sincronizada… (enlace)», or «Conforme con REN-001» for v1.
- **Second valley: presenter anxiety.** During a live run the matrix reflows and the held column greys out just as the audience is watching. The elapsed clock («Evaluando v2 · 2 de 3 · 0:12») partly reassures.

#### What's Working

- The transit-line ledger fulfils the product's core promise of seeing why v1 passes, v2 fails and v3 is held. At 1440×900 the three verdicts, each delivery's deciding test outcome («Prueba «cancelado no genera aviso»: fallida» / «Ninguna prueba vinculada a REN-001») and the provenance are visible in the first viewport. A header pinned on scroll keeps them visible while reading. Stages with an identical result collapse into one spanning cell, scope tags separate the deciding stage from context, and station rings carry state through shape as well as colour.
- The human-in-the-loop governance flow is careful at the high-stakes moment. The WIQL fingerprint has a copy control. Discarding with an empty note gives inline validation (aria-invalid, aria-describedby, the field focused, a specific message). The confirm text states the consequence (an existing task is updated, otherwise a new one is created). Focus lands on «Cancelar», Esc backs out to «Aprobar», a 5-second «Deshacer» grace period follows, and a failed submission retries without losing the note. The «Decidir en el expediente de v2» row scrolls to the right dossier and focuses the note field.
- Keyboard and safety engineering suits a live demo. R only moves focus, never runs. Paid runs need a second press. The engine switches to «Solo evidencia · 0 tokens» when a cache exists. Esc closes the topmost panel first and needs two presses to stop a run. scroll-padding-bottom matches the docked sheet so focused elements are never hidden. Esc returns focus to the last inspected cell. prefers-reduced-motion and forced-colors are handled.

#### Priority Issues

**[P1] Signals outside REN-001 take on the REN-001 state vocabulary, so severity reads inverted, and blue and amber each carry several meanings.**

- Why: A CISO watching live sees stage 3 (8 open CodeQL alerts; the SecOps agent flags one py/redos alert as «Severidad alta») and stage 7 (27.78 % 5xx) labelled «Informativo», while stage 6 (one low posture observation) is «Atención requerida». The explanation («Los hallazgos SecOps de severidad alta se muestran aparte») sits only in the guide. Blue simultaneously means brand, primary action, «Atención requerida», «Informativo · por revisar» and «Evaluando». Amber means «Evidencia insuficiente» in the header and «Sin confirmar» in the deciding row for the same v3. This erodes trust in exactly the five-second read the product promises.
- Fix: Split the two axes visibly. Reserve the verdict and state vocabulary for the rows that decide REN-001 (stages 4 and 8). Give context stages their own severity chip taken from the data («8 alertas · 1 alta», «5xx 27,8 % · sin línea base»), in an outline style that does not compete with verdicts. Move «Atención requerida» off the brand blue, or give it a shape-only treatment. Rename v3's stage-4 state to «Sin prueba vinculada» so the deciding row speaks the verdict's language. The guide's state list should drop from six bullets to four.
- Command: /impeccable colorize

**[P2] The «Decide REN-001» row doesn't show the deciding evidence, and no C# code or TRX message appears anywhere in the UI.**

- Why: In stage 4, v1 («Verificado») and v2 («Incumplido») both read «4 pruebas ejecutadas en TRX», and v3 reads «3 pruebas ejecutadas». The inspector for stage 4/v2 adds only counts and «fallida». The dossier gives a file path plus links to the raw TRX and log in new tabs. The STORY promises xUnit cases, C# code and CLI output, so QA/SecOps have to leave the console to see why v2 fails.
- Fix: Put the outcome of the linked test in each stage-4 cell: «CanceladoNoGeneraAviso · falló en Assert.Empty(datos.Avisos)», «aprobada», or «sin prueba con Trait REN-001». In the inspector and the dossier proof band, show the 6–10 lines of RenovacionesTests.cs around line 20 with the assertion highlighted, plus the TRX error-message excerpt (expected empty, found 1 aviso).
- Command: /impeccable clarify

**[P2] The docked stage inspector covers half the viewport, and its controls scroll away inside it.**

- Why: At 1440×900 the fixed sheet is 450px tall. With the 45px pinned header, only about 3 stage rows stay visible, so «inspecciona cualquier etapa sin perder de vista la matriz» only half holds. At presentation zoom it gets worse. Scrolling the sheet's content hides v1/v2/v3, Anterior, Siguiente and Cerrar. The sheet also overlaps the «Expediente por entrega» heading and tabs.
- Fix: Make .inspector-topbar sticky inside the sheet and cap the sheet at about 38vh with an expand toggle. Better: render the inspector as an expanded row directly under the inspected stage, spanning the delivery columns, so the matrix context stays above and below it. Drop the compare grid when the matrix row above already shows the comparison.
- Command: /impeccable layout

**[P2] Starting or finishing a live run reflows the whole matrix.**

- Why: renderLedger only merges stages that are identical across deliveries when every shown delivery has finished (finished.length === shown.length). As soon as one column turns «Evaluando», stages 1, 2, 3, 6 and 7 split from one spanning cell into three narrower ones. Row heights jump and summaries truncate, then everything jumps back when the run ends. This happens while the presenter is narrating, and the held column also turns greyscale.
- Fix: While running, keep a spanning cell whenever the finished deliveries agree and the running delivery's held result matched, and draw a busy treatment on the busy column's part of that span. Alternatively reserve the row heights. Keep the red/green ink on held cells and mark them stale with opacity or a hatched overlay rather than filter: grayscale(1).
- Command: /impeccable harden

**[P2] At narrow widths and 200% zoom, the three-column ledger breaks.**

- Why: At 720px CSS width (1440 at 200% zoom), v3's «Evidencia insuficiente» badge spills past the ledger's right edge. At 390px it overflows its own pill (89 > 86px), scenario text wraps to six lines, the pinned header's «Etapa» collides with «v1», stage-5 summaries shrink to «ca-…», and the masthead pills wrap to three lines. This affects low-vision zoom users as well as phones.
- Fix: Below about 760px, switch the ledger to stacked rows per stage with v1/v2/v3 as labelled sub-lines (or a delivery switcher above the ledger). Let badges wrap inside the column with max-inline-size: 100%. Hide the pinned header's «Etapa» corner when it has no room. Collapse the ecosystem links into one «Sistemas conectados» disclosure.
- Command: /impeccable adapt

#### Persona Red Flags

- **Alex (Impatient Power User)**: V cycles versions forward only (no Shift+V), and no key jumps from the inspected stage to that delivery's decision; he has to Tab to «Abrir expediente de vN». The browser Back button never undoes stage stepping because the hash uses history.replaceState. When he scrolls long stage data in the 450px sheet, the toolbar (v1/v2/v3, Anterior, Siguiente, Cerrar) scrolls out of reach. Deciding v2 and v3 means two tab switches, two confirms and two 5 s grace periods, with no queue of pending decisions. That is deliberate HITL, but it feels serial. Pressing R then Enter to start a run makes the matrix reflow under him.
- **Sam (Accessibility-Dependent)**: Shared-cell buttons say the same phrase twice: «Etapa 1, Planificar, igual en v1, v2 y v3: Verificado Igual en v1, v2 y v3 …». Stage 7's accessible name runs to about 200 characters and is read on every Tab. The inspector's version buttons announce «v2, pressed» with no verdict, unlike the dossier tabs («v2: Incumplido»). The help drawer is a plain section with no dialog or landmark role, and it closes silently once focus passes «Cerrar guía» and the shortcuts checkbox. At 200% zoom (720px) the v3 badge spills outside the ledger, and truncated summaries («ca-appcontratos ·…») can only be read in full in the inspector. Ledger text is 12–13px at 100%. On the positive side: skip link, 3px focus ring, live regions, aria-invalid on the note field, focus returned to the last cell on Esc, and glyph plus colour for every state.
- **Jordan (First-Timer, as the executive in a live demo)**: Jordan must decode three verdicts, five stage states, «· por revisar» and «· sin línea base» qualifiers, and «Sin datos». The same amber v3 is «Evidencia insuficiente» in the header and «Sin confirmar» in the «Decide REN-001» row. Stage 3 (8 SAST alerts, one rated alta by the agent) and stage 7 (27.78 % 5xx) are «Informativo» while stage 6 is «Atención requerida», which reads backwards. TRX, WIQL, SHA-256, SAST, CSPM, KQL, MAF, HITL and the «Núcleo determinista» interchange all need hovering over abbr tooltips or opening the guide. The deployment-drift claim «Azure ejecuta v1, con cambios locales sin publicar» sits in a 13px cell note. On mobile, the dossier tabs shrink to bare ✓ × ? glyphs, and Anterior/Siguiente become icon-only.

#### Minor Observations

- The «verified-stage chips» and «card stage rows» named in the brief do not exist in this build. Stages open from ledger cells, from the station row header (pointer only; keyboard users reach the same stage through the cells), from keys 1–8 and from the hash. «Solo brechas» hides clean rows and shrinks verified cells in mixed rows to the state label only.
- Nested cards, measured: .results and .command-deck have a 14px radius with a 1px border, and .ledger-cell-btn inside has a 10px radius with a 1px border (stages 3 and 5–8). Inspector compare columns are also boxed inside the sheet. The direction contract explicitly rejects «tarjetas anidadas».
- The governance task title («[REN-001][v2] Corregir exclusión…») is shown unlabelled between the fingerprint and the note field. «Aprobar en Azure Boards» doesn't name what it creates or updates; the confirm step explains it only afterwards.
- Terminology drift: the inspector asks «¿Qué debía resolver esta versión…?» while the catalogue and controls say «entrega». The guide's states section uses filled circular pips, while the ledger legend uses bare glyphs for the same states.
- The programmatically focused inspector sheet shows its focus-visible outline as a second rounded frame floating around the sheet's top edge on desktop and mobile.
- The run-state headline can still say «corridas en caché (0 tokens)» while a live run is in progress, because finished columns are cached. That is accurate but reads oddly next to «Evaluando…».
- The page relies on the system sans stack only. Even under the CSP, a self-hosted face or a deliberate monospace treatment for hashes, fingerprints and test names would give the evidence a typographic identity.
- The footer repeats the shortcut list already shown in the guide and in the inline key hints.

#### Cognitive Load

Moderate load: 3 of 8 checklist items fail.

**Fails:**
- **Minimal choices:** several decision points show more than 4 options.
- **Working memory:** the dossier shows one delivery at a time, so comparing v2 and v3 decisions relies on memory. The open sheet leaves only about 3 stage rows visible. State qualifiers must be recalled from the guide.
- **Single focus:** about 10 controls and roughly 20 lines of copy compete with the matrix in the first viewport.

**Passes:** chunking (DevSec 4 + CloudOps 4), grouping, one thing at a time (governance per delivery), progressive disclosure («Gestionar :5080», «+3 pruebas», agent disclosures, the guide drawer), and visual hierarchy, though blue overload weakens it.

**Decision points with more than 4 visible options:**
1. First viewport: 3 ecosystem links, «Abrir portal activo», «Gestionar :5080», «Guía», «Alcance» (4 options), «Motor», «Ejecutar evaluación» and «Solo brechas», about 10 in all.
2. Inspector toolbar: v1, v2, v3, Anterior, Siguiente, Cerrar (6).
3. Governance panel: copy fingerprint, note, Aprobar, Descartar, 5 artifact links and 2 agent disclosures (about 11).
4. State vocabulary on one screen: 3 verdicts, 5 stage states, 2 qualifiers and «Sin datos» (about 11 meanings), with amber and blue each doing double or quadruple duty.
5. Guide shortcut list: 7 bindings.

«Gestionar :5080» expanded shows 4 buttons, which is at the limit.

#### Detector and Measured Checks (B)

- cramped-padding: <div> "sandbox-strip": children flush against bg on all sides (no inset)
- Browser: Overlay not run: the page CSP blocks script injection. The header comes from assessment/ui.py:181-182: "default-src 'self'; ... script-src 'self'".
- Browser: Mutation preflight in a new tab (index 4) at http://127.0.0.1:8051/: setting document.title worked. An appended inline <script> was connected to the DOM but never ran (window flag stayed unset). An external <script src=http://localhost:59999/probe.js> fired onerror.
- Browser: Fallback signal: two securitypolicyviolation events fired, 'script-src-elem inline' and 'script-src-elem http://localhost:59999/probe.js'. The console logged the matching 2 CSP errors. Both were caused by the probe, not by the app.
- Browser: Consequence: the live server was not started, detect.js was not injected and no 'impeccable'-prefixed console messages exist. No user-visible overlay is available. Running detect.js through CDP evaluate was deliberately avoided, because it would not be the overlay and live-server stop could rewrite the project's HTML entry.
- False positive: cramped-padding on .sandbox-strip (CLI reports line 0; real source is index.html:65 and style.css:347-350): likely a false positive. The strip has padding 6px block and 0 inline, but it holds no bare text. Its child .frame.sandbox-bar is centred, with a measured inline inset of 73px at 1440 and 12px at 390. The pill text #sandbox-pill sits 19px from the strip's top and 18px from its bottom. The #sandbox-toggle text is inset by the button's own 12px inline padding inside a 44px-tall bordered box. Admitted: the 6px block padding is below the detector's 8px guidance, but it pads boxed 44px controls, not text touching the strip's edge.
- False positive: th.ledger-corner renders at font-size 0 at 390px (text 'Etapa', no aria-hidden). This is an intentionally visually hidden column header that screen readers still get, not an illegible-text defect.
- False positive: In the running-state preview, the status says 'Agentes MAF' while the Motor select still shows 'Solo evidencia · 0 tokens', and the summary keeps '(0 tokens)'. This comes from the task's injected setStatus string in a simulated state, not a real UI inconsistency.
- False positive: Low token-level ratios are not rendered failures. --state-warn-dot (2.15 on #fff) and --state-pass-dot are only used for .sandbox-dot, which sits on the navy strip #0d2b59 next to a text label: measured 6.49 and 5.49. The idle dot, --border-strong #9ab5dc, measures 6.65 on navy. --state-info-dot (2.54 on #fff) is defined but unused in style.css.
- False positive: --border-strong at 2.1:1 on white and --state-fail-dot at 2.66 as the border of the armed .sandbox-stop (fill --state-fail-ink #7f1d1d): token-level only. The usages are decorative dividers or borders of filled or text-labelled controls, which are exempt from the 1.4.11 3:1 rule. Interactive control borders use --border-control, measured 4.64:1 on white.
- False positive: .sr-only spans and visually hidden .tab-state spans show scrollWidth greater than clientWidth (cw=1, overflow hidden). This is the intended visually hidden pattern, not overflow.
- Measured: Console errors (app's own): 0 errors and 0 warnings across 4 page loads (default view, after the running preview, and the deep link #etapa=8&version=v2). The only errors in the session were the 2 CSP errors caused by the injection probe.
- Measured: Horizontal page overflow, 1440x900: scrollWidth 1425 equals clientWidth 1425. 0 visible elements extend past the viewport without a clipping parent. Same result with the inspector open: 0.
- Measured: Horizontal page overflow, 390x844: scrollWidth 375 equals clientWidth 375, 0 unclipped offscreen elements and 0 inner horizontal scrollers, both in the default view and with the inspector open.
- Measured: Content overflowing its own box (overflow visible) at 390: the ledger header badge 'Incumplido' has content 85px in an 81px box (+4px); 'Evidencia insuficiente' has 89px in 81px (+8px). Their parents span.ver-head-row overflow by +3 and +7px. The screenshot shows the 'Incumplido' chip cut at its right edge ('Incumplid') against the v3 column. Ledger buttons for stages 4 and 5 overflow by +2 to +6px (89px box). div.frame.topbar overflows by +6px (357 vs 351). At 1440 the same scan finds 0 elements.
- Measured: Mobile header weight at 390: the header plus the sandbox strip is 313px tall (37% of the 844px viewport) before the h1, which starts at 347px. The nav pill 'Azure Boards · AB#1' wraps to about 3 lines (112x59). GitHub and CodeQL wrap to 2 lines (112x44). Header and strip are position static, not sticky.
- Measured: Interactive targets: 1440 default view has 40 visible targets, 0 under 44x44 and 0 under 24x24. 390 default view: 40 targets, 0 under 44 and 0 under 24. With the inspector open (deep link): 48 targets at both sizes, 0 under 44 and 0 under 24.
- Measured: Text contrast at 1440, 36 distinct foreground/background pairs on visible text: 0 below AA. Lowest pairs: --ink-on-navy on #1f5fc4 (line bullet 'CO', 12px) 5.65; --ink-muted #435c82 on canvas #f2f6fc 6.26; on #f7faff 6.49; on #fff 6.79 (43 elements, min 12px); --state-warn-ink on --state-warn-bg 8.17; --state-fail-ink on --state-fail-bg 8.53; --state-pass-ink on --state-pass-bg 8.82; --state-info-ink on --state-info-bg 8.86; --ink-secondary 10.3 to 11.6 on tinted backgrounds; --ink-on-navy-muted on #081c3a 12.01. No gradient backgrounds and no reduced opacity in the sampled ancestry.
- Measured: Text contrast at 390, default view and inspector open (including single-character labels such as stage numbers and kbd hints): minimum 5.65, 0 failures.
- Measured: Smallest text at 390: 3 ledger header badges at 11px ('Verificado', 'Incumplido', 'Evidencia insuficiente'). 12px is used for line bullets, scope tags and legend chips. The bulk of the text is 13px (138 elements).
- Measured: Focus-visible, desktop, 14 Tab stops (skip-link, 3 nav links, Abrir portal :5080, Gestionar :5080, Guía, scope select, mode select, run button (focused, not activated), Solo brechas, ledger cells 1 to 3): every stop matched :focus-visible and had a solid 3px outline with 2px offset. Ring #1d4ed8 on light surfaces measures 6.70 on #fff and 6.18 on #f2f6fc. Ring #7dd3fc on navy measures 8.36 on #0d2b59 and 10.18 on #081c3a. Skip link present and first in order.
- Measured: [hidden] overridden by CSS: 15 elements carry [hidden] and 0 have computed display other than none, at 1440, at 390 and with the inspector open.
- Measured: Reduced motion in style.css: 16 transition/animation declarations sit inside @media (prefers-reduced-motion: no-preference) (lines 2507+). 2 sit outside it: style.css:1123 (.ledger-cell-btn background-color/border-color 140ms, colour only, acceptable) and style.css:1485 (.toggle-chevron 'transition: rotate 140ms', spatial motion, NOT gated). The reduce block (2627) only adds a 200ms linear fade-in to the stamped badge.
- Measured: Reduced motion, measured in the running-state preview: without emulation, 3 infinite animations run (spin 800ms, dot-breathe 1100ms, track-run 1300ms) plus alert-in 240ms. Under emulated reduce, 0 animations are running, but .toggle-chevron still computes 'rotate 0.14s cubic-bezier(0.16,1,0.3,1)'. Verdict: not every animation is gated; the one exception is the chevron rotate.
- Measured: Reduced motion in app.js: animateIn (line 305) swaps translate for opacity 0.4 to 1 under reduce. All 3 scrollIntoView/scrollBy calls (lines 879, 1108, 2251) use behavior 'auto' under reduce. setInterval at line 358 is a timer tick. setInterval at line 1862 is a text countdown for the decision grace period, not visual motion.
- Measured: Inspector open state (deep link #etapa=8&version=v2): section.stage-inspector is position fixed, display grid, focus is moved to #stage-inspector. At 1440 it is 1280x450 with top 450 (covers the lower half of the viewport). At 390 it is 351x422 with top 422 (covers the lower half and overlaps the ledger).
- Skipped: impeccable live-server start (--background), detect.js injection, reading 'impeccable'-prefixed console messages and live-server stop: skipped because the CSP script-src 'self' blocks both inline and external injected scripts (see browser_findings).
- Skipped: Governance panel preview (Aprobar en Azure Boards / Descartar confirmation step): optional, not exercised. No governance buttons were clicked.
- Skipped: Focus-visible walk was done at desktop 1440 only (14 stops). No Tab walk at 390 and no walk inside the open inspector or the dossier tabs.
- Skipped: Dossier (expediente) tab panels were not opened by clicking. Only the deep-linked stage inspector state was measured.
- Skipped: No forbidden controls were activated: no Ejecutar evaluación, Evaluar vN, Reintentar, Iniciar vN, Detener :5080 and no R key. Only Tab was pressed. The running state was simulated through the task-provided console snippet and cleared by reload.
- Skipped: Side effects: Playwright wrote snapshots and screenshots to the gitignored .playwright-mcp/ (assess-b-mobile-390.png, assess-b-running-1440.png, assess-b-inspector-390.png). One screenshot briefly landed in the project root as assess-b-desktop-1440.png and was moved to /private/tmp/claude-501/-Users-johnbenjamincastrosanabria-Developer-AppContratos/83d39608-fc2e-4bb3-8fc9-8aa7e54c5b74/scratchpad/assess-b-desktop-1440.png. Final git status matches the starting snapshot. Both of my tabs (index 4) were closed; the user's tabs 0 to 3 were untouched.

#### Questions to Consider

- What if only the rows that decide REN-001 (4 and 8) spoke in verdict language, and the other six became a compact context strip with its own severity scale? Would the matrix then answer REN-001 in one line?
- Why is v2's most persuasive fact, the failing Assert.Empty(datos.Avisos) with one aviso generated, a sentence in a tab rather than the visual centrepiece of the console?
- v2 and v3 are the only pending decisions. Why does the dossier show them one tab at a time instead of side by side, where the difference between «regresión» and «brecha silenciosa» would be obvious?
- Does the «Núcleo determinista» interchange row earn its space in a live demo, or is it a metaphor the presenter has to explain every time?
