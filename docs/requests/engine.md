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
