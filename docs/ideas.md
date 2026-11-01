- Line net amount field; document-type column -> credit note; split combined 'PLZ Ort' columns; Excel rates 0.19 -> 19; duplicate invoice numbers in row_per_invoice mode (from mapping agent, 31 Oct)
- Self-hosted IBM Plex fonts (website request 1): deferred, system-ui for v1; needs a pinned build-time download (31 Oct)
- UX: disable 'Speichern und umwandeln' (or ask inline) while a field required for the chosen profile (e.g. BT-10 for XRechnung) is unmapped; today the user converts 5 invoices and gets 0 valid (found in wave-3 browser e2e, 1 Nov)

## From wave 4 (1 Nov 2026)
- "Gutschrift" can also mean a self-billed invoice (Gutschrift i. S. d. § 14 Abs. 2 Satz 2 UStG, type 389), not a credit note; `doc_type` treats it as 381 for now. Offer a choice on the mapping page.
- Server-side block of conversions with unmapped required fields (today UI only; such invoices fail validation and are not offered).
- Free limit is per e-mail address (review L7); revisit with payments.
- Consent proof retention after unsubscribe set to 3 years — owner to confirm.
- Cloudflare build command could append `&& python ops/scripts/check_site.py` (needs CLAUDE.md change).
