# Engine progress

## 2026-10-31 — wave 1 (engine agent, branch `agent/engine`)

### What was built
- Package `engine` (`engine/__init__.py`) with the frozen API from `contracts/mapping.md`:
  `build_cii(invoice, profile="xrechnung")`, `build_zugferd(invoice)`, `validate(data, filename="")`,
  `render_pdf(invoice)`, re-exports `FeatureUnavailable`, `InvoiceInputError` from `contracts.types`.
  Extra helpers: `totals_warning(invoice)`, `compute_totals(invoice)` (see requests).
- `engine/inputcheck.py`: input checked against `contracts/invoice.schema.json` (Draft 2020-12 + FormatChecker),
  errors become `InvoiceInputError([RowError(row=0, field=<JSON Pointer>, code, message_de)])`. Messages
  never contain invoice values. Engine checks on top: BT-10 for XRechnung only (BR-DE-15), IBAN mod-97,
  IBAN required for XRechnung credit transfer (BR-DE-23-a), exemption reason for every E/AE/K/G/O used,
  seller needs VAT id or `company_id` (BR-CO-26, see open issues).
- `engine/cii.py`: CII D16B generator. Decimal from strings, ROUND_HALF_UP; computed totals; BT-24
  `…#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0` (xrechnung) or `urn:cen.eu:en16931:2017` (zugferd);
  BT-23 only for XRechnung; BT-31 (VA) and BT-32 (FC); BT-30; per-category BT-120/BT-121 from
  `vat_exemptions`, never for S or Z; category O: no line rate (BR-O-05), header rate 0 (BR-DE-14);
  381 + BG-3; means 58/30 with IBAN/BIC; BT-9 and/or BT-20; BG-14 period; EAS scheme from input.
- `engine/validation.py`: format detection (CII / UBL / PDF via `facturx.get_xml_from_pdf`), safe parsing
  (5 MB limit, `resolve_entities=False`, `no_network=True`, `huge_tree=False`, no DTD, any DOCTYPE rejected,
  only the re-serialised tree goes to Saxon). Layers XSD, EN16931 (CEN XSLT + BR-CO-25 supplement),
  XRechnung (only for the XRechnung profile), KoSIT (only with `KOSIT_VALIDATOR_JAR`, else
  `ran=False`, "KoSIT-Prüfer nicht installiert"). Validity rule exactly as in the contract
  (`APP_ENV` staging/prod requires KoSIT). Saxon executables compiled once per process, guarded by a lock.
- `engine/messages_de.py`: 30 German messages (BR-DE-1..7/15/16/19/21/23-a, BR-16, BR-62/63, BR-CO-10/13/15/16/17/25/26,
  BR-S-08, BR-E-10, BR-Z-10, BR-AE-10, BR-O-02/10, BR-50, BR-61); a test checks every ID exists in the pinned
  rules. Unknown IDs: "Regel X nicht erfüllt. Originaltext: …". `text_en` always holds the original rule text
  (for BR-DE rules that original is German).
- `engine/pdf.py`: `render_pdf` — A4, German labels, multi-page table, embedded Vera fonts (shipped with
  reportlab, no system fonts). `render_pdfa3b` makes the same visual PDF/A-3b and has it approved by
  `pikepdf.pdfa` (allowlist validator).
- `engine/zugferd.py`: Mustang path (see spike). CLI wrappers `engine/generate.py`, `engine/validate.py` call the package.
- Removed stale generated files in `engine/out/` (old generator output, not conformant).

### How to run
```
python -m pytest engine/tests -q            # from repo root (61 tests, ~2 s)
python engine/generate.py engine/samples/schreinerei.json /tmp/r.xml --pdf [--profile zugferd]
python engine/validate.py /tmp/r.xml [--json]
```
Bare `pytest` does not work yet (importlib mode does not put the root on sys.path) — see request.

### Test results
- 61 passed. Both samples valid. KoSIT test suite CII regression: 39/41 (unchanged baseline; failures
  04.05a and 02.01a are BR-CL-10/13/21 code-list rules where the pinned CEN head differs from KoSIT's lists).
  The suite test is skipped when `/home/claude/itplr-kosit/xrechnung-testsuite` is absent.

### ZUGFeRD spike result (time-boxed, ~30 min)
- reportlab visual with embedded TrueType fonts + `pikepdf.pdfa.save(..., "3b")` → **passes** pikepdf's
  allowlist PDF/A-3b validator (after removing reportlab's empty `/Trans` and Helvetica defaults in tables).
- factur-x embedding of the XML → **cannot be verified locally**: pikepdf's validator reports embedded files
  and the Factur-X XMP extension schema as "unsupported" (it approves only what it knows; it is not veraPDF),
  and veraPDF/Mustang are not downloadable here.
- Decision: no unverified hybrid is offered. `build_zugferd` raises `FeatureUnavailable` unless `MUSTANG_JAR`
  is set; with Mustang it runs `--action combine` (PDF/A-3b base + EN16931 XML, `--format zf --version 2
  --profile E --no-additional-attachments`) and then `--action validate`, returning the file only when the
  summary status is `valid`. The Mustang path is tested with a mocked subprocess only — **must be verified in
  Docker/CI with the pinned Mustang CLI** (flag names may differ between Mustang versions).

### Stubbed / not verified here
- KoSIT layer: command line (`java -jar <jar> -s <config>/scenarios.xml -r <config> -o <dir> file`) and VARL report
  parsing are tested with a fake report only. Needs a real run in CI.
- Mustang (above). PDF/A validation of uploaded PDFs in `validate()` is not done (only the embedded XML is checked).

### Open issues
1. BR-CO-26 vs schema: the schema accepts a seller with only `tax_number`, but EN 16931 requires BT-29, BT-30
   or BT-31. The engine rejects tax-number-only sellers without `company_id`. Kleinunternehmer without USt-IdNr.
   and without register entry cannot be invoiced until BT-29 (seller identifier) is added — contract request.
2. BR-CO-25 is missing from the pinned CEN CII stylesheet 1.3.17; the engine checks it itself (labelled
   "engine supplement" in `text_en`). A test fails once CEN adds it back, so the supplement can be removed.
3. Code-list differences CEN head vs KoSIT config (two suite files). KoSIT in CI is the authority.
4. UBL input is reported as "not checked" (all layers skipped), per v1 scope.
5. `engine/validate.py` and `engine/generate.py` are scripts; importing `engine.validate` as a submodule would
   shadow the `validate` function on the package. Nobody should import them.

## 2026-11-01 — wave 4 fix round (review findings H3, H5, M11, M1, L6)

### What changed
- **H3** `engine/validation.py`: BT-24 matched exactly (`describe_guideline`). Recognised and compliant:
  XRechnung (`…#compliant#urn:xeinkauf.de:kosit:xrechnung_X.Y`, extension), Factur-X/ZUGFeRD EN16931
  (`urn:cen.eu:en16931:2017`), BASIC, EXTENDED. MINIMUM/BASIC-WL → error `PROFILE-NOT-EINVOICE` (German, with BMF
  source URL) in the EN16931 layer → invalid. Anything else → profile `unknown`, error `PROFILE-UNKNOWN`
  ("Unbekanntes Profil … keine E-Rechnung nach EN 16931"), and `is_valid` never accepts `unknown`.
  The Report now has `guideline_id` (request 7).
- **H5** `inputcheck.py`, `cii.py`: `seller.seller_id {id, scheme?}` satisfies BR-CO-26 and is written as
  `ram:SellerTradeParty/ram:ID` (or `ram:GlobalID schemeID=…`) before `ram:Name`. Seller with only seller_id + tax
  number passes XSD/EN16931/XRechnung (tests for both profiles and with scheme 0088).
- **M11** PDF input gets a `PDF/A` layer: skipped "PDF/A-3-Konformität nicht geprüft" without Mustang; with
  `MUSTANG_JAR`, `--action validate` decides (the `<pdf>` section of Mustang's XML); failures make the file invalid.
- **M1** KoSIT: process-wide `BoundedSemaphore` (`KOSIT_MAX_PARALLEL`, default 2, read once), `layer_kosit_many`
  runs one JVM for up to 200 files (timeout 120 s + 2 s/file, max 1800 s); `engine.validate_many(items)` uses it.
  `validate()` unchanged in signature.
- **L6** Already correct; now pinned by tests: 381 without explicit due date has no BT-9; BG-3 with date emitted.
- Tests: `XRECHNUNG_TESTSUITE_DIR` for the suite test; opt-in `test_engine_real_tools.py` (`ENGINE_REAL_TOOLS=1`).

### How to run
`python -m pytest -m "not network" engine -q` (95 passed, 2 real-tool tests skipped; whole suite 362 passed).

### Stubbed / not verified here
- KoSIT multi-file CLI call and per-file report naming (`<stem>-report.xml`) tested with a fake only; the real-tool
  test verifies it in CI once ops adds the step (request 12).
- Mustang PDF/A parsing assumes `<validation><pdf>…<summary status=…/></pdf>…`; unverified against the pinned CLI.
  Any other output → layer shown as skipped, never passed.

### Open issues
- Skipped PDF/A does not make a PDF invalid (validity rule lists XSD/EN16931/XRechnung/KoSIT only). If the
  orchestrator wants PDF/A required in staging/prod, add it to the validity rule (request 8).
- BASIC accepted as compliant — confirm (request 7).
- App still derives `format` from the namespace and calls `validate` per invoice (requests 7, 10).
