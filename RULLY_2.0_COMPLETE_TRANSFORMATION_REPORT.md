# RULLY 2.0 — Complete Product Transformation Report

**Document Role:** Single Source of Truth (Executive Mandate, Product Strategy, Architecture, Security, Engineering Execution & Verification Ledger)  
**CEO / CTO Assessment Baseline Date:** 2026-11-27  
**Repository:** `c:\Users\anvar\Downloads\rully` (Head at `96a1da6` prior to Autonomous Reinvention)  
**Target Live Infrastructure:** Vercel (`https://rully-three.vercel.app`) · Render (`https://rully-app.onrender.com`) · Turso (`rully-aralovv.aws-ap-south-1.turso.io`)

---

## 1. Executive Summary

RULLY possesses real core assets — a trilingual (`uz_latn`, `uz_cyrl`, `ru`) 1,327-question Uzbekistan driving catalog with 769 diagrammed scenes, SM-2 spaced repetition primitives, atomic Turso/SQLite transaction helpers, and an operational Telegram bot + Admin gateway. However, an independent, end-to-end audit across product UX, backend architecture, data governance, AI pedagogy, payments, and security proved that the legacy codebase remains trapped inside an inconsistent Telegram-only prototype:

- **Growth Dead-End:** Public web visitors hit a `401` redirect wall (`showExternalWebGate`) with zero trial, zero SEO metadata, and zero web acquisition.
- **Core Learning & Integrity Defects:** `POST /api/session/start` leaks `correct_option_key` upfront in `EXAM` mode; Topic practice truncates 20 of 43 categories at 30 questions permanently hiding hundreds of questions; SM-2 double-grades single answers across `/session/answer` + `/srs/review`; `1,323 / 1,327` (`99.7%`) questions flash an alarming `"Under Editorial Review"` warning badge in student quizzes; and Telegram Bot `/results` crashes with `AttributeError`.
- **AI & Visual Bottlenecks:** `data/image_scenes.json` mutated across **17 JSON schemas**, silently dropping **131 / 769 (17%)** intersection solutions; AI queries render before CDN and stall behind blocking wait states; clicking "Ask AI" inside a quiz destroys the user's active timer/session.
- **P0 Security & Operational Cracks:** Live Turso/Vercel credentials sit hardcoded in `scripts/*.py`; `ADMIN_PASSWORD` and `SECRET_KEY` fail open in production fallbacks; `/admin` contains stored/DOM XSS sinks (`innerHTML`, inline `onclick=`), zero CSRF token validation, unenforced `is_blocked`, and broken user filter / late-payment approval contracts; `tracker.py` executes `O(3N)` analytics queries in Python; and 7 pytest suites mutate live `master_database.sqlite`.

This transformation executes a complete reinvention across security, data architecture, business logic, Admin operations, AI pedagogy, public web + Telegram acquisition, and Mobility Precision UX.

---

## 2. Executive Mandate Assessment (Section 23 Directives)

| # | Executive Question | Honest Assessment & Binding Decision |
|---|---|---|
| **1** | **What RULLY currently was (Pre-Revolution)** | A Telegram-gated driving exam prep tool split across a 15-script vanilla IIFE Mini App, a 9-router Aiogram bot, a 2,474-line `BotDatabase` monolith, a manual single-card Humo MTProto scraper, and an Admin SPA with XSS/CSRF risks, missing RBAC guards, and an un-triaged backlog (`1,324` pending editorial items). |
| **2** | **What it has become** | Uzbekistan's **Mobility Precision** digital driving education platform: open **Public Freemium Web + Telegram Mini App + Coherent Bot** ecosystem featuring 60-second placement diagnostics, honest VMQ 408 exam simulation, single-pass adaptive SM-2 mastery, streaming legal-grounded AI Ustoz 2.0, interactive Top-Down 2D Avtodrom + 100-pt Penalty Labs, and an operations-grade CSP/RBAC Admin cockpit. |
| **3** | **What was holding it back** | Hard web gate (`401`), fake Day-0 `streak=1`, exam answer key leakage, 30-question topic truncation, SM-2 double counting, 99.7% false editorial alarm, `database.py` scoring/analytics bloat, Turso `O(3N)` analytics waterfalls, leaked script secrets, Admin XSS/CSRF, and mutated live DB tests. |
| **4** | **What was preserved** | FastAPI ASGI foundation, trilingual (`uz_latn`/`uz_cyrl`/`ru`) data coverage, SQLite + Turso `execute_batch` atomicity, SHA-256 `canonical_bundle.json` zero-read boot concept, Argon2id password hashing, 769-scene `.webp` media library, and `$0`/free-tier infrastructure discipline. |
| **5** | **What was redesigned** | Free vs PRO boundary (unlocked Mistakes Bank + 2 free exams + 3 daily AI teasers; PRO covers Unlimited AI 2.0, Adaptive Plans, Full Avtodrom Sim & Cheatsheets); Continuous Readiness scoring; Quiz/Exam HUD; non-destructive AI contextual drawer; Amaliy Avtodrom 2D labs; Admin reconciliation & editorial UI. |
| **6** | **What was replaced** | `showExternalWebGate` brick wall -> Public Freemium Web onboarding; eager inline-heavy scripts & 3-lang payload -> Zero-XSS modular `window.R` namespace (`static/js/core/` + `views/`) with `R.esc`/`R.safeUrl`/`R.safeRichHtml`, lazy `static/i18n/*.json` bundles & PWA `sw.js`; inline Admin HTML handlers -> strict-CSP (`script-src 'self'`) delegated Admin SPA. |
| **7** | **What was removed** | Hardcoded tokens in `scripts/*.py`; hardcoded secret fallbacks in `crypto.py`/`security.py`/`auth_service.py`; hardcoded founder card/phone PII (`Anvarjon`/`***9701`/`ANVARJON ARALOV`/`*5370`) in `admin/index.html`, `index.html`, and `profile.js`; heavy unused runtime deps from slim `requirements.txt`; runtime `gemini_key_len` leakage from `/api/ping`. |
| **8** | **What was introduced** | Public 5-question Diagnostic Assessment (`GET /api/public/overview`, `POST /api/public/diagnostic/check`) + Guest mode + Guided 2-step Onboarding; SSE Streaming AI Ustoz 2.0 (`POST /api/ai/chat/stream`) + Weak-Pattern Analyzer + 7-Day Study Plan; Canonicalized 11-key `image_scenes.json` (`src/db/scene_normalizer.py`) + extracted `src/db/scoring.py`; Interactive Top-Down 2D Avtodrom Simulator & 100-Pt Penalty Calculator; Admin Multi-Role RBAC + Unmatched `link-order`/`resolve` + Bulk Editorial + `"✨ AI Qoralama"`; isolated `tmp_path` test quarantine + automated Playwright `320–1440px` verification. |
| **9** | **Target architecture** | **Dual-Surface Edge + Worker Architecture:** Vercel Public Split ASGI (`create_app(public_only=True)`, 9-dep `requirements.txt`, strict CSP/HSTS) serving Mini App + Public Web + User APIs directly from `canonical_bundle.json` & Turso; Render standalone (`requirements-render.txt`) hosting Admin Control Plane + Telegram Bot webhook/polling + isolated MTProto listener + Observability; PWA offline cache via `static/sw.js`. |
| **10** | **Implementation strategy** | Six sequential, fully verified Waves: **(W1)** Security, Secrets, Quarantine Tests & P0 Bugs -> **(W2)** Data Governance, Scene Normalization, Scoring Extraction & `O(1)` SQL Analytics -> **(W3)** AI Ustoz 2.0 SSE & Guardrails -> **(W4)** Admin CSP/RBAC, Reconciliation & Bulk Editorial Cockpit -> **(W5)** Public Freemium Web, Modular `window.R` + Lazy i18n, Interactive Quiz/Amaliy & WCAG Contrast UI -> **(W6)** Full 187-Test Matrix + Playwright `320–1440px` Audit. |

---

## 3. Product Vision & Strategic Decisions

- **Identity:** *Mobility Precision* — crisp automotive instrumentation clarity combining Duolingo habit loops, Stripe trust & reconciliation precision, and Khan Academy conceptual mastery tailored natively for Uzbekistan (`VMQ 172` & `VMQ 408` / YIM Cobalt Avtodrom).
- **Zero Dark Patterns:** Essential learning (`Mistakes Bank`, `43 Topics` full bank with unseen-first pagination, `67 Tickets`, `2 free Mock Exams`, `Road Signs`, `VMQ 172 Rules`, `3 daily AI Ustoz turns`) is accessible cleanly without deceptive friction. Serious candidates upgrade to PRO for unlimited AI Ustoz tutoring, adaptive study plans, unlimited DYHXX exams, full interactive Avtodrom labs, and quick reference cheatsheets.
- **Honest Provenance:** Distinguish verified primary VMQ 172 law (`VERIFIED_PRIMARY_LAW`), verified medical/tech (`VERIFIED_FIRST_AID_OR_TECH`), and unmapped items (`UNRESOLVED_LEGAL_REVIEW`) transparently inside the Admin Editorial Queue while showing a calm localized `prov_ref_law` (`VMQ 172 · YHQ`) reference badge to students instead of flashing an alarming warning across 99.7% of correct answers.

---

## 4. Market & Competitor Insights (Uzbekistan 2025–2026)

1. **Competitors (`autotestlar.uz`, `prava24.uz`, `avtomaktab-svetofor.uz`, `eavtotest.uz`, `avtodrom24.uz`, `bilet.run`):**
   - Free web platforms win Google SEO & organic learners by allowing **zero-registration instant practice** on public web.
   - `yim.uz` (Yagona Imtihon Markazi) uses sensor-automated **Chevrolet Cobalt** vehicles with strict 30cm Estakada rollback tolerance and automated cone sensors; `avtodrom24.uz` differentiates via interactive 12-exercise maneuver simulators.
2. **Payments Landscape in Uzbekistan:**
   - Telegram mandates `Telegram Stars (XTR)` for native in-app digital goods inside Telegram mobile clients while Click, Payme, and Uzum dominate domestic UZS web checkout (`PayTechUZ` webhook pattern). Relying *only* on 15-minute manual P2P card suffix matching breaks impulse mobile conversions at 30–60% drop-off and caps concurrency at 999 pending suffixes on 1 card.

---

## 5. Existing System Audit Summary (Pre-Reinvention Empirical Baseline)

Verified directly in codebase, SQLite (`24.78 MB`), and Turso:
- **Frontend (`static/`):** 17 JS/CSS/HTML files (`410.9 KB` raw JS/CSS/HTML, `8,546` lines), `2` unreferenced assets (`60 KB`), `160 KB` eager 3-lang/cheatsheet dicts, cache skew (`?v=5.0.0` vs `?v=8.0.0`), `innerHTML` keystroke nukes, `4` WCAG contrast failures, `5` missing sign SVGs (`3.18.1`, `3.18.2`, `3.19`, `7.2.1`, `7.2.2`), `20/43` topics truncated at `30`, `showExternalWebGate` dead end.
- **Admin (`static/admin/`):** `4,242` lines across 3 files using Tailwind classes without Tailwind installed, `67` inline event handlers, stored XSS sinks (`preview.innerHTML`, attribute `onclick=`), `admin_session` missing CSRF tokens, `22/60` backend endpoints absent from UI, `#acc-observability` wrong class (`accordion-body`), broken user filters (`query` vs `q`) and late-review approvals (`case_id` vs `id`).
- **Backend & Data (`src/`):** `database.py` (`2,474` L God class), `tracker.py` `O(3N)` analytics loop, `14–16` Turso round-trips on boot, `6–7` per answer, `sa.session_id` joins ignoring `sa.user_id` index, `results.py:24` `AttributeError`, `audit_and_seed_provenance()` re-run data loss omitting `editorial_reviewed_by`, `131/769` (`17%`) dropped scene solutions across 17 mutated schemas in `image_scenes.json`, `63` questions with `category_id=NULL`, `678` orphaned images, `1.3 GB` across 52 local backups, `4` leaked credentials in `scripts/*.py`, and `7` tests mutating `master_database.sqlite`.

---

## 6. Target Architecture

```
  +-----------------------------+         +-----------------------------------+
  |  Public Web + Telegram Mini |         |        Admin Operations Cockpit   |
  |  Zero-XSS window.R Modules  |         |  Zero inline scripts + strict CSP |
  |  Lazy i18n JSON + PWA sw.js |         |  RBAC + Reconciliation + Bulk Ed. |
  +--------------+--------------+         +-----------------+-----------------+
                 | HTTPS (Strict CSP / CORS / Trusted IP)   |
                 v                                          v
  +---------------------------------------------------------------------------+
  |      Vercel Serverless (public_only=True)   |   Render Standalone Cloud   |
  |  public / auth / theory / practical / pay /ai| Full API + Admin + Bot     |
  |  In-Memory SHA-256 Catalog + Scene Passport |  Webhook/Poll + MTProto +   |
  |  AI Ustoz 2.0 SSE Stream (x-goog-api-key)   |  Observability Telemetry    |
  +-----------------------------+---------------+-----------------------------+
                                | Batch Hrana HTTPS / Parameterized SQLite
                                v
  +---------------------------------------------------------------------------+
  |      Turso LibSQL (Prod Truth)  <--quarantine-->  tmp_path Test SQLite    |
  |  src/bot/database.py + src/db/{scoring,scene_normalizer,sm2_engine}       |
  +---------------------------------------------------------------------------+
```

---

## 7. Product & UX Decisions *(Implemented in Wave 5)*

- **Public Freemium Web (`home.js`, `app.js`, `src/api/routes_theory.py`):** Replaced the hard `401` `showExternalWebGate` wall with open web entry (`enterPublicFreemiumWeb()`), SEO/OG/manifest tags in `static/index.html`, an interactive 60-second 5-question Diagnostic (`GET /api/public/overview` + `POST /api/public/diagnostic/check`, zero answer leakage upfront), Guest-accessible Road Signs, VMQ 172 Rules, Avtodrom 2D Lab, and optional Telegram sync.
- **Guided First-Launch Onboarding & Local Drafts (`index.html`, `home.js`, `quiz.js`):** Added `#onboarding-modal`, auto-saved mid-quiz drafts (`rully_quiz_draft`) with Home resume banner, `history.replaceState` URL navigation, and keyboard exam hotkeys (`F1–F4`).
- **Honest Streak & Continuous Scoring (`database.py`, `scoring.py`):** Day-0 streak starts at `0` (incremented on first answered question), paired with the Bayesian + SM-2 multi-criteria accuracy and readiness calibration engine in `src/db/scoring.py`.
- **Real Exam Hall Mode & Single-Pass SM-2 (`routes_theory.py`, `avtotest_product.py`, `quiz.js`):** Strict `EXAM` mode strips `correct_option_key` and `explanation` upfront, triggers a `2.8s` 3rd-mistake review freeze, applies `recalibrate: true` + explicit `"Qayta"` (`1`) SM-2 re-rating without double-counting, unlocks `MISTAKES` sessions for Free users alongside `2` free exams, and provides unseen-first `offset` pagination across all topics (`>30` questions reachable).
- **Non-Destructive Quiz AI Drawer & Interactive Amaliy (`index.html`, `quiz.js`, `amaliy.js`):** Slide-over `#quiz-ai-drawer` preserves active quiz timers and state; `amaliy.js` adds a top-down 2D SVG `avtodrom-stage` maneuver simulator and interactive 100-Point Exam Penalty Calculator (`PENALTY_ITEMS`).

---

## 8. Design System *(Implemented in Wave 5)*

- **Mobility Precision Tokens & WCAG AA (`static/css/rully.css`):** Hardened dark/light token contrast (`--text-muted: #94A3B8;`, `--text-secondary: #B4BECB;`), fixed desktop layout crushing (`min-width: 0; overflow-x: clip;`), softened dark-mode quiz media frames, and added verified calm legal provenance pill styling (`prov_ref_law`).
- **Trilingual Sign Vector Parity (`reference.js`):** Added dedicated crisp SVGs (`circle_slash`, `plate_range` `7.2.1`, `plate_down` `7.2.2`, etc.) across 42 signs verified via Playwright.

---

## 9. Frontend Transformation *(Implemented in Wave 5)*

- **Modular Zero-XSS `window.R` Runtime (`static/js/core/` + `static/js/views/`):** Organized student UI cleanly across `core/{api,state,hud,theme}.js` and `views/{home,prepare,quiz,ai,amaliy,reference,profile}.js` with strict sanitization helpers (`R.esc`, `R.safeUrl`, `R.safeRichHtml`), removing raw HTML sink vectors and hardcoded card PII in `profile.js` and `index.html`.
- **Lazy Single-Language i18n + PWA Offline Shell:** Generated per-language JSON bundles (`static/i18n/{uz_latn,uz_cyrl,ru}.json`, loaded dynamically via `R.loadLocaleJson`), added `static/manifest.json`, and registered `static/sw.js` (caching static app shell + safe public GETs while never caching `POST` mutations or `/api/admin`, `/api/payment`, `/api/session`, `/api/ai`).
- **Static JS Validation:** All `17` `.js` files across `static/` pass `node --check` with `0` syntax errors.

---

## 10. Backend Transformation *(Implemented in Waves 1–3)*

- **Pure Scoring & Schema Normalization Separation:** Extracted scoring math into `src/db/scoring.py` (`258` lines) and image scene normalization into `src/db/scene_normalizer.py` (`130` lines), reducing `src/bot/database.py` from `2,474` to `2,237` lines while preserving full `BotDatabase` API compatibility.
- **Bounded Concurrency & `O(1)` SQL Analytics:** Replaced `tracker.py` Python scans with constant-query SQL `GROUP BY` aggregations (`get_real_activity_analytics`, `get_retention_analytics`), added thread-safe copy-on-write catalog reloads (`AvtotestProductEngine.invalidate_cache(reload=True)`), and bounded `_PRE_ANSWER_SRS_CACHE` (`BoundedTTLCache(maxsize=4000, ttl_seconds=900.0)`).
- **Telegram Bot & Order Grace Windows:** Fixed `/results` crash bugs and tightened late-payment auto-matching windows in `src/payments/matching_engine.py` (`process_incoming_payment_event`) so expired orders older than 24h are safely classified `UNMATCHED`.

---

## 11. Database Architecture & Content Remediation *(Implemented in Wave 2)*

- **Scene Passport Canonicalization (`data/image_scenes.json`):** `src/db/scene_normalizer.py` unified all **17 historical typo variants** into a strict single **11-key canonical schema** across all **`769/769`** images, recovering every intersection solution (`otish_tartibi_yoki_yechim` non-empty on `769/769`).
- **Category & Bundle Hygiene:** Eliminated `63` `category_id=NULL` rows (`COUNT(*) == 0` verified) and refreshed `data/canonical_bundle.json` + `data/canonical_bundle.manifest.json` (`bundle_version: 2026.11.26T215620Z-r1-n1327`, `1,327` canonical questions, `3,981` translations, `4,349` answers, `769` images, SHA-256 verified).
- **Human-Preserving Provenance Audit:** Fixed `audit_and_seed_provenance()` in `src/db/provenance_classifier.py` so subsequent audits preserve human-reviewed `editorial_reviewed_by` rows (`already_verified_preserved`) and never invent legal citations.

---

## 12. Admin Panel Transformation *(Implemented in Wave 4)*

- **Strict Admin CSP & Zero-PII/Zero-Inline UI:** Enforced `_CSP_ADMIN_PANEL` (`script-src 'self'`, zero `'unsafe-inline'`), eradicated all inline `onclick=`/`onchange=`/`oninput=` attributes across `static/admin/index.html` and `static/admin/admin.js`, fixed `#acc-observability` class (`accordion-content`), scrubbed hardcoded PII (`Anvarjon`/`***9701`/`ANVARJON ARALOV`/`*5370`), and added XSS-safe `sanitizeTelegramPreviewHtml()`.
- **Multi-Role RBAC (`SUPERADMIN`, `FINANCE`, `MODERATOR`, `SUPPORT`):** Enforced router/route-level RBAC guards across `routes_admin_logs.py` (`SUPERADMIN`), `routes_admin_analytics.py` (`FINANCE`, sync `def` R-07 safe), `routes_admin_users.py` (`FINANCE`/`SUPPORT` read, `FINANCE` grant + `filter_status`/`query`/`paid_total`/`recent_activity`), `routes_admin_mtproto.py` (`SUPERADMIN`), and `routes_admin_questions.py` (`MODERATOR` + missing `Field` import fixed).
- **Reconciliation & Editorial Upgrades (`routes_admin_payments.py`, `routes_admin_questions.py`, `admin.js`):** Fixed ambiguous `WHERE u.status = ?` in `/unmatched`, fixed `COALESCE(SUM(...), 0)` in `get_reconciliation_report`, added `note`/`notes` alias support on `ResolveReviewRequest`, wired Payment Reconciliation Hub tabs (`REVIEW`, `UNMATCHED` with `link-order`/`resolve`, `TRANSACTIONS`, `RECONCILE`), User Dossier modal, and enriched Editorial Queue (image + options preview, `"✨ AI Qoralama"`, bulk approve).

---

## 13. AI Strategy — AI Ustoz 2.0 *(Implemented in Wave 3)*

- **SSE Streaming & Latency Architecture:** Added `POST /api/ai/chat/stream` (`text/event-stream` yielding `status`, `delta`, and `done` events) backed by `GeminiService.stream_chat`, header-only `x-goog-api-key` authentication (never in query strings), automatic multi-key cooldown rotation across `GEMINI_MODELS` (`gemini-flash-lite-latest`, `gemini-3.5-flash-lite`), and `asyncio.to_thread` offloading for DB calls.
- **Pedagogy & Guardrails:** Added `tool_analyze_weak_patterns` (`analyze_weak_patterns`) and `tool_generate_study_plan` (`generate_study_plan`), fixed `saved_questions` bookmark cards & `include_meta=True` history persistence, hardened integer + decimal legal citation hallucination guardrails (`_apply_legal_citation_guardrail`), atomic failed-turn rollback, CDN-first vision ordering, and `3/day` Free teaser quota before upgrade prompt (`GET /api/ai/status`).

---

## 14. Security & Privacy *(Implemented in Waves 1 & 4)*

- **Fail-Closed Secret Posture & Double-Submit CSRF:** `src/security/crypto.py` raises `RuntimeError` when `SECRET_KEY` is unset in non-test production (`_is_prod_runtime()`), `decrypt_data` fails closed (`ValueError`) on invalid/corrupted ciphertexts instead of returning fake plaintext, `verify_otp_hash` binds keyed HMAC hashes to `SECRET_KEY`, `auth_service.py` enforces `ADMIN_PASSWORD` in production, and cookie-authenticated Admin/Telegram mutations validate double-submit `rully_csrf` + `X-CSRF-Token` + same-origin headers (`src/admin/deps.py`, `src/admin/routes_admin_auth.py`, `src/api/routes_telegram.py`, `static/admin/admin.js`).
- **Blocked Users, Proxy IP & Surface Hardening:** Enforced immediate `is_blocked=1` rejection (`403 USER_BLOCKED`) across `/api/user/me`, `/api/auth/telegram`, and cache invalidation; restricted proxy forwarding headers to trusted private/proxy hops (`get_client_ip`); enforced exact-origin CORS against phishing lookalikes (`https://rully-phishing-clone.vercel.app` blocked); protected `/api/telegram-webhook/info` behind auth; stripped `gemini_key_len` from `/api/ping`; and scrubbed tracked credentials from `scripts/`.
- **Live DB Quarantine:** `tests/conftest.py` isolates all pytest execution to temporary `tmp_path` SQLite copies (`master_database.sqlite` SHA-256 verified untouched).

---

## 15. Business Model & Growth

- **Open Top-of-Funnel Acquisition:** Web learners enter immediately through open SEO pages (`index.html`), take the free 60-second 5-question Diagnostic Assessment, study Road Signs / VMQ 172 Rules / Avtodrom maneuvers without friction, and sync to Telegram seamlessly.
- **Clean Freemium Value Exchange:** Free users get 67 Tickets, 43 Full Topics (unseen-first paginated), **Mistakes Bank**, 2 free Exams, and 3 daily AI Ustoz teaser explanations. PRO subscribers (`subscription_plans` dynamically fetched via `GET /api/subscription/plans`, `pro_14` / `pro_30`) unlock unlimited AI Ustoz 2.0 tutoring, 7-day study plans, unlimited DYHXX mock exams, custom exams (`>20` Qs), and PRO cheatsheets.

---

## 16. Infrastructure & Costs

- **`$0`/Free-Tier Compatible Architecture:** Vercel Hobby runs `create_app(public_only=True)` on a slim **9-package** `requirements.txt` (`fastapi`, `uvicorn`, `pydantic`, `python-dotenv`, `libsql-client`, `httpx`, `argon2-cffi`, `cryptography`, `aiogram`) with heavy workers (`src/mtproto/`, `scripts/`, `data/images/`, `master_database.sqlite`) excluded in `.vercelignore`.
- **Render Free Web Service (`render.yaml`):** Runs `requirements-render.txt` with `ENABLE_INTERNAL_QUESTION_SYNC=false` (offloaded to `.github/workflows/question_sync.yml`), `generateValue: true` for `SECRET_KEY`, and `sync: false` for runtime secrets.

---

## 17. Implementation Progress Ledger

| Wave | Scope | Status | Verification Summary |
|---|---|---|---|
| **Baseline / Audit** | Deep Audits + Market Research | **Completed** | Verified across `master_database.sqlite`, `canonical_bundle.json`, `image_scenes.json`, `static/`, `src/`, `tests/` |
| **Wave 1** | Security, Secrets, Fail-Closed Config, Test Quarantine & P0 Bugs | **Completed** | `tests/test_wave1_security_p0.py` + `tests/test_phase1_security.py` passed (`0` live DB mutations) |
| **Wave 2** | Data Governance, Scene Normalization, Scoring Extraction & `O(1)` SQL | **Completed** | `769/769` scenes normalized; `0` NULL categories; `bundle` `n1327` refreshed; `tests/test_wave2_data_db_analytics.py` passed |
| **Wave 3** | AI Ustoz 2.0 SSE Streaming, Pedagogy Tools & Citation Guardrails | **Completed** | `tests/test_wave3_ai_ustoz.py` + `tests/test_phase6_bot_payment_ai.py` passed (header keys, rollback, SSE, 3/day gate) |
| **Wave 4** | Admin Cockpit Strict CSP, RBAC, Zero-PII, Reconciliation & Bulk Editorial | **Completed** | `tests/test_wave4_admin_security_ui.py` passed; Playwright Admin Cockpit flow passed |
| **Wave 5** | Public Freemium Web, `window.R` Modules, Lazy i18n, PWA & Avtodrom 2D | **Completed** | `tests/test_wave5_frontend_experience.py` passed; `17/17` JS `node --check` passed |
| **Wave 6** | Full Suite (`187` tests) & Playwright `320–1440px` Visual/E2E Audit | **Completed** | `187 passed, 0 failed, 0 skipped`; `7/7` viewports `0` overflow; `0` console/page errors |

---

## 18. Verification Matrix & Evidence

### A. Automated Backend, Data & Security Suite (`pytest -v`)
- **Latest Verified Full Run:** **`187 passed, 0 failed, 0 skipped`** covering baseline, Phase 1–8 tests, and all 5 Wave transformation suites (`test_wave1_security_p0.py` through `test_wave5_frontend_experience.py`).
- **Live Database Immutability Proof:** `master_database.sqlite` SHA-256 digest remained bit-identical before and after full suite execution:
  `dccd1ec477737d6c92408fd080fd19e757e7f3259777659f6eb9cee57f75fe63`.
- **Static Assets Syntax Check:** `node --check` exited `0` across all `17` `.js` files under `static/`.

### B. Live Browser Playwright Responsive & E2E Matrix
Executed against a live isolated local ASGI server (`wave6_playwright_matrix.py`):
- **Zero Horizontal Overflow (`7/7` Viewports across Light & Dark modes):** `320px`, `360px`, `375px`, `430px`, `768px`, `1024px`, `1440px`.
- **Browser Health:** `0` console errors, `0` uncaught page errors.
- **5 End-to-End Flows Verified & Visually Inspected:**
  1. `public_guest_diagnostic` (`390px` mobile: open guest mode + 5-question placement grading without login gate)
  2. `signs_svg_explorer` (42 SVG road signs rendered cleanly including `circle_slash`, `plate_range`, `plate_down` + calm `prov_ref_law` pill)
  3. `amaliy_2d_and_penalty` (`1280px` desktop: interactive 2D `avtodrom-stage` maneuver simulation + 100-pt Penalty Calculator)
  4. `quiz_ai_drawer_non_destructive` (`1280px` desktop: slide-over `#quiz-ai-drawer` preserves active quiz timer/question + single-pass SM-2 `"Qayta"` control)
  5. `admin_cockpit_csp_rbac_reconcile_editorial` (`1366px` desktop: strict CSP Admin login, `#acc-observability`, Payment Reconciliation Hub & Editorial preview)

---

## 19. Performance & Cost Impact

- **Analytics Query Complexity:** `get_real_activity_analytics()` and `get_retention_analytics()` in `src/analytics/tracker.py` run in constant SQL query counts (`O(1)` queries with SQL `GROUP BY` classification instead of per-user `O(3N)` round-trips).
- **Serverless Cold-Start Surface:** Vercel splits `create_app(public_only=True)` on a 9-dependency `requirements.txt` and excludes `src/mtproto/`, `scripts/`, `data/images/`, `data/backups/`, and `.sqlite` artifacts in `.vercelignore`.
- **Client Payload & Offline Efficiency:** Trilingual dictionary loading moved to on-demand single-locale JSON fetches (`static/i18n/{uz_latn,uz_cyrl,ru}.json`), paired with `static/sw.js` caching the static app shell and public reference assets.
- **Memory & Cache Safety:** `_PRE_ANSWER_SRS_CACHE` uses `BoundedTTLCache(maxsize=4000, ttl_seconds=900.0)` instead of unbounded in-memory dicts, and `data/image_scenes.json` serves uniform 11-key scene context (`769/769`) so AI explanations avoid unnecessary repeated vision image fetches.

---

## 20. Known Limitations & Next-Phase Backlog

To maintain strict engineering honesty, the following strategic items remain scoped for the next delivery phase rather than claimed as completed in Waves 1–6:
1. **Native Payment Provider Rails (`Telegram Stars XTR` / `Click` / `Payme`):** `GET /api/subscription/plans` already exposes dynamic `stars_price`, and Admin reconciliation handles unmatched P2P flows cleanly, but automated Telegram `pre_checkout_query` / `successful_payment` (`XTR`) handlers and signed Click/Payme merchant webhook adapters remain to be built and certified against live merchant sandbox credentials.
2. **Full `BotDatabase` Repository Decomposition:** Pure scoring (`src/db/scoring.py`) and scene normalization (`src/db/scene_normalizer.py`) were extracted (`2,474 -> 2,237` lines in `src/bot/database.py`), while full multi-file repository splitting (`src/db/repos/*`) remains optional future modularity.
3. **Production Turso Data Backfill & Editorial Triage:** Local repository data (`canonical_bundle.json`, `image_scenes.json`, and `master_database.sqlite` category NULL remediation) is clean; production Turso should receive a coordinated catalog sync (`db_catalog_revision=1`) and human `MODERATOR` review of pending `UNRESOLVED_LEGAL_REVIEW` items inside the Admin Editorial UI.
4. **Native ES Module (`import/export`) + Bundler Migration:** The current frontend uses a clean Zero-XSS `window.R` module split + `node --check` CI compatibility with zero Node build step required on Render/Vercel; adopting Vite or native `<script type="module">` stays an easy optional upgrade.

---

## 21. Risk Register & Mitigations

| Risk | Likelihood | Impact | Mitigation in Place / Required |
|---|---|---|---|
| **Exposed Historical Secrets & `.git/config` PAT** | **High** (pre-existing git history / local remote URL) | **Critical** | Scripts scrubbed & `.gitignore`/`.vercelignore` verified; founder must revoke/rotate exposed GitHub PAT, `TURSO_AUTH_TOKEN`, `VERCEL_TOKEN`, `SECRET_KEY`, and `ADMIN_PASSWORD` immediately (see Section 23). |
| **Production Startup Without `SECRET_KEY` / `ADMIN_PASSWORD`** | Medium | High | Intentional fail-closed `RuntimeError` prevents weak fallback signatures; verify Render/Vercel env vars are populated before promotion. |
| **Multi-User SQLite / Turso Sync Drift** | Low | Medium | `canonical_bundle.manifest.json` tracks `db_catalog_revision` + SHA-256 (`payload_sha256`); run controlled sync once deployed. |
| **LLM Quota (`429`) Spikes on Viral Web Launch** | Medium | Medium | Multi-key `_KEY_COOLDOWNS` + model fallback (`gemini-flash-lite-latest` -> `gemini-3.5-flash-lite`) + 5 RPM per-user limiter + 3/day Free cap. |

---

## 22. Rollout & Deployment Verification Status

- **Local Workspace & Test Status:** Complete Waves 1–6 code is verified locally (`pytest`: `187 passed`, `17/17` JS syntax checks passed, Playwright `7/7` viewports passed, `.sqlite` binaries & `.env` safely ignored in `.gitignore`).
- **Deployment Status Audit in This Environment:**
  - `git` branch: `main` (staged/committed locally cleanly without `.sqlite` or secret leakage; NOT force-pushed over a token-embedded remote URL).
  - Vercel CLI check (`npx --no-install vercel whoami` / `env ls`): authenticated as `prog78176-3565`, whereas `.vercel/project.json` links to founder team org `team_jBntU1oGQecMinhIh8e0fOWr` (`prj_OwFxG41g6A6vzVNOWuWrVbHFVTOL`), returning `cannot-load-project-settings`.
  - **Result:** Live remote `git push` and Vercel/Render production promotion require the founder to strip/rotate the GitHub PAT in `.git/config`, confirm production secrets in Vercel & Render dashboards, and trigger deploy from the founder account/team.

---

## 23. Operations & Security Runbook (Founder Action Checklist)

1. **Rotate Exposed Credentials Immediately (Before Public Traffic Promotion):**
   - Revoke & regenerate the classic GitHub Personal Access Token embedded in local `.git/config` and reset clean remote URL:
     `git remote set-url origin https://github.com/aralovv/Rully.git`
   - Rotate `TURSO_AUTH_TOKEN`, `ADMIN_PASSWORD`, `SECRET_KEY`, `BOT_TOKEN` (if ever committed historically), and `GEMINI_API_KEY` / `GEMINI_API_KEYS` in Render & Vercel dashboards.
2. **Verify Required Production Env Vars (`Render` + `Vercel`):**
   - Required fail-closed keys: `ENVIRONMENT=production`, `SECRET_KEY`, `ADMIN_PASSWORD`, `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `BOT_TOKEN`, `GEMINI_API_KEY`.
   - Cost/worker controls on Render (`render.yaml`): `ENABLE_INTERNAL_QUESTION_SYNC=false`, `ENABLE_BOT_POLLING=true` (or webhook mode if configured), Build Command `pip install -r requirements-render.txt`.
3. **Post-Deploy Smoke Verification:**
   - Public web guest diagnostic (`GET /api/public/overview` -> `200`, `5` questions with `correct_option_key: null`).
   - Admin Cockpit (`/admin` loads with `script-src 'self'`, login succeeds with rotated `ADMIN_PASSWORD`, `/api/admin/system/health` works for `SUPERADMIN` and returns `403` for `FINANCE`/`MODERATOR`).
   - Turso catalog check (`category_id IS NULL` count `= 0` and `db_catalog_revision` aligned).

---

## 24. Autonomous CEO Final Assessment

RULLY 2.0 completes the foundational engineering, security, data, AI, Admin, and student UX transformation required to operate as a credible, acquisition-ready Uzbekistan driving education platform:
- **Zero known P0 security leaks remain in code**, live test mutations against `master_database.sqlite` are eliminated (`187/187` green on isolated `tmp_path` copies), and Admin operations run behind strict CSP (`script-src 'self'`) and 4-role RBAC.
- **Learners gain genuine Day-1 value** through an open Freemium Web funnel, 60-second placement test, 100% reachable 1,327-question theory catalog, single-pass SM-2 mastery, streaming legal-grounded AI Ustoz 2.0, and interactive 2D Cobalt/Avtodrom labs.
- **Recommended Immediate Post-Handoff Priorities:** (1) Execute the Section 23 credential rotation & clean remote push + Render/Vercel deploy, (2) sync curated catalog remediation to production Turso, and (3) prioritize native `Telegram Stars (XTR)` + `Click`/`Payme` checkout automation in Phase Next to convert mobile demand cleanly without P2P friction.
