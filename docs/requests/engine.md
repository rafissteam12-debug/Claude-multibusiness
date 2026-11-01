# Requests from the engine agent (2026-10-31)

## 1. Contract: seller identifier BT-29 (BR-CO-26) — high
`party_seller` accepts `tax_number` alone, but EN 16931 BR-CO-26 needs BT-29, BT-30 or BT-31. Such invoices
are invalid. Proposal: add `seller_id` (BT-29, string, optional `seller_id_scheme`) to `party`, and change the
`party_seller` anyOf to `vat_id | company_id | seller_id`; keep `tax_number` (BT-32, needed for BR-DE-16) separate.
Stub now: engine raises `InvoiceInputError` (`/seller/company_id`, `missing_required`) when neither `vat_id`
nor `company_id` is present. Seller profile schema and mapping need the same field.

## 2. Contract: RowError codes used by the engine — medium
`contracts/mapping.md` lists mapping codes only. The engine additionally uses: `invalid_value`, `bad_iban`,
`missing_exemption`, `forbidden_exemption` (plus `missing_required`, `bad_number`, `bad_date`). Please add them.

## 3. Contract: totals warning — medium
`validate(data, filename)` cannot see `source.expected_totals` (it is never written into the XML). The engine
exports `totals_warning(invoice) -> dict | None`; the app should set
`report["totals_warning"] = engine.totals_warning(invoice)` after `validate(build_cii(invoice))`.
Please add `totals_warning` to the frozen engine API in `contracts/mapping.md`.

## 4. Config: `KOSIT_CONFIG_DIR` — medium
The KoSIT validator needs the XRechnung configuration (`scenarios.xml` + resources) besides the jar.
New variable `KOSIT_CONFIG_DIR` (default: the directory of `KOSIT_VALIDATOR_JAR`). Please add to
`contracts/config.md` and `.env.example`; ops should install the configuration there.

## 5. Root `pyproject.toml`: `pythonpath = ["."]` — low
With `--import-mode=importlib`, bare `pytest` does not put the repo root on sys.path, so `import engine` /
`import contracts` fail. `python -m pytest` (used by `make test`) works. Adding
`pythonpath = ["."]` under `[tool.pytest.ini_options]` makes both work.

## 6. Ops: Mustang flags and dependencies — medium
- Verify in Docker/CI with the pinned Mustang CLI: `--action combine --source base.pdf --source-xml factur-x.xml
  --out out.pdf --format zf --version 2 --profile E --no-additional-attachments` and `--action validate --source out.pdf`
  (expects `<summary status="valid"`). Adjust `engine/zugferd.py` if the flags differ.
- `engine/requirements.txt` now includes `jsonschema>=4.18`, `pikepdf[pdfa]>=10.16`, `pypdf>=4`.
- `.gitignore`: `engine/out/` can be ignored entirely (generated output; removed from the repo).

## Status (orchestrator, 31 Oct)
1 done (seller_id BT-29; BR-CO-26 = vat_id | company_id | seller_id). 2, 3, 4, 5 done in contracts/pyproject. 6 -> ops agent (wave 2). Engine: please emit BT-29 when seller_id is present (follow-up in wave 2 fix round).

# Requests from the engine agent — wave 4 fix round (2026-11-01)

## 7. Contract: Report key `guideline_id` — high (H3)
`validate()` now returns `"guideline_id": "<BT-24 as found>" | null` next to `profile`. Please add it to the
Report in `contracts/mapping.md`. The app should derive `format` from it instead of the root namespace
(`app/check.py detect_format`), e.g. with `engine.validation.describe_guideline(gid) -> (profile, level, compliant)`;
level is `XRECHNUNG`, `EN16931`, `BASIC`, `EXTENDED`, `MINIMUM`, `BASIC-WL` or None.
Validity rule addition for `contracts/mapping.md`: "`profile` must be `xrechnung` or `zugferd`; `unknown` is never
valid. MINIMUM and BASIC-WL carry error `PROFILE-NOT-EINVOICE` in the EN16931 layer; unknown ids carry
`PROFILE-UNKNOWN`." Decision to confirm: BASIC (`…#compliant#urn:factur-x.eu:1p0:basic`) is accepted as compliant
(BMF 15.10.2024 excludes only MINIMUM and BASIC-WL); say so if it should be rejected too.

## 8. Contract: layer name `PDF/A` — medium (M11)
For PDF input the Report has a fifth layer `{"name": "PDF/A", ...}` after KoSIT. Without `MUSTANG_JAR` it is
`ran=false, skipped_reason="PDF/A-3-Konformität nicht geprüft"` (visible, never counted as passed). With Mustang it
runs `--action validate`; errors (`PDFA-3`) make the file invalid. Please add `"PDF/A"` to the layer name list in
`contracts/mapping.md`; UIs that list layers must show it.

## 9. Config: `KOSIT_MAX_PARALLEL` — medium (M1)
Maximum number of KoSIT JVMs running at the same time per process (default 2). Please add to `contracts/config.md`
and `.env.example`. Size it to the VPS RAM (each JVM ~1 GB with `-Xmx1g`).

## 10. Engine API addition: `validate_many` — medium (M1)
`validate_many(items: list[tuple[bytes, str]]) -> list[Report]` (same order; one KoSIT JVM per chunk of 200 files).
Please add to the engine API in `contracts/mapping.md`. App: use it for conversion jobs instead of one `validate`
per invoice; call it in a worker thread (the KoSIT semaphore blocks).

## 11. Config: `XRECHNUNG_TESTSUITE_DIR` — low
Checkout root of `itplr-kosit/xrechnung-testsuite`; `engine/tests/test_engine_kosit_suite.py` reads it (default
`/home/claude/itplr-kosit/xrechnung-testsuite`, skipped when absent). Please add to `contracts/config.md`; ops may set it in CI.

## 12. Ops: opt-in real-tool tests — low
`ENGINE_REAL_TOOLS=1 python -m pytest engine/tests/test_engine_real_tools.py` with `KOSIT_VALIDATOR_JAR`,
`KOSIT_CONFIG_DIR`, `MUSTANG_JAR` set runs single and batched KoSIT (verifies the multi-file CLI call and the
`<name>-report.xml` naming) and the Mustang PDF/A layer. Please add a CI step in the tools image (ops). Add
`ENGINE_REAL_TOOLS` to `contracts/config.md` as a test-only variable.

## 13. Content: help text for BT-29 — low (H5)
The engine now accepts the seller identifier (BT-29, `seller.seller_id`) for BR-CO-26 and writes it into the XML.
`content/help/fehlermeldungen-verstehen.md:67` still says only USt-IdNr./HRB work.

## Status (orchestrator, 1 Nov, wave 4)
Wave 4 items merged into contracts/ (mapping.md, api.md, config.md), .env.example and .github/workflows/ci.yml; deferred items in docs/ideas.md.
