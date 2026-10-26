# Ablaufwerk (working name)

Independent venture workspace. Not connected to BestBroker4U in any way: own code,
own brand, own accounts (none created yet), own budget (EUR 0 discretionary).

## Layout

| Path | What it is | Status |
| --- | --- | --- |
| `belegbruecke/` | Demo converter: invoice export (JSON) -> XRechnung 3.0 CII XML (+ illustrative hybrid PDF) | Working, validated |
| `belegbruecke/validate.py` | Three-layer validator: CII D16B schema, CEN EN 16931 rules, KoSIT XRechnung rules | Working; 39/41 official CII test files pass (2 fail on upstream code-list rules) |
| `belegbruecke/sch2xslt.py` | Minimal Schematron -> XSLT compiler for the KoSIT rules | Working for the XRechnung CII rule set only |
| `site/` | Offer page draft (German) | Draft, not published |
| `content/` | AI creator concept, first scripts, tracking plan | Drafts, nothing published |

## Run the demo

```
python belegbruecke/generate.py belegbruecke/samples/schreinerei.json belegbruecke/out/RE-2026-0418.xml --pdf
python belegbruecke/validate.py belegbruecke/out/RE-2026-0418.xml
```

Dependencies: Python 3.11+, `lxml`, `saxonche`, `factur-x`, `reportlab`.
Rule sets (not vendored here; fetched from their public repositories):
- CEN EN 16931 CII XSLT and CII schema: github.com/ConnectingEurope/eInvoicing-EN16931
- KoSIT XRechnung Schematron v2.6.0 (2026-08-31): github.com/itplr-kosit/xrechnung-schematron
Set `EINV_VENDOR` and `EINV_KOSIT` to their local paths.

## Known limits (honest list)

- The CEN layer uses the repository head, not the exact rule version pinned in the
  KoSIT validator configuration of 2026-08-31. Before a customer delivery, re-check
  with the official KoSIT validator.
- The hybrid PDF embeds the XRechnung XML for illustration. A conformant ZUGFeRD file
  also needs PDF/A-3 and the ZUGFeRD profile identifier; not built yet.
- The converter does not decide VAT category or rate. It takes them from the input.
- Demo data is fictional (example.invalid-style addresses, example IBAN).
