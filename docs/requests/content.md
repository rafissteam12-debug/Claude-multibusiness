# Requests from the content agent

1. **pyproject.toml – add `content/tests` to `testpaths`.** File: `content/tests/test_content_files.py` (stdlib + pytest only).
2. **contracts/api.md – unsubscribe endpoint.** Welcome mails (`content/emails/03-*`, `04-*`) contain `{{ unsubscribe_url }}`
   and the opt-in mail promises a one-click unsubscribe link in every mail. Suggest `GET /api/v1/unsubscribe?token=` (shows
   confirm button) + `POST` (consumes), same token rules as opt-in, PUBLIC.
3. **contracts/api.md / app – mail template variables.** E-mails use `confirm_url`, `login_url`, `requested_at`,
   `source_label`, `check_url`, `site_url`, `app_url`, `unsubscribe_url` and Jinja `{% include "_footer.md" %}`
   (see `content/emails/README.md`). App agent renders Markdown -> HTML + plain text.
4. **Consent text v1.** The double opt-in mail describes the subscription (two intro mails + occasional notes on
   e-invoice rule changes). Orchestrator: confirm this matches the consent text stored as version `v1` and the cut
   "Brevo newsletter list" decision; if only transactional mails are allowed, drop the "gelegentlich Hinweise" bullet.
5. **Engine – BR-CO-25.** `engine/rules/cen/EN16931-CII-validation.xslt` (pinned head) contains no assertion for BR-CO-25
   (payment due date BT-9 or payment terms BT-20 when amount due > 0). Help text and guides explain BR-CO-25 as a common
   error. Please confirm whether the KoSIT configuration still enforces it, and that `message_de` exists for it.
6. **Site – `?ref=ig-00N` on `/e-rechnung-pruefen`.** Ada posts track via the bio link `?ref=ig-001..004` and subscribe
   `source: "ig-..."`. Site should pass `ref` into the `subscribe` source and `events` `code`.
7. **App – free-plan limit behaviour.** Help article states: only valid invoices count; uploads/mapping unlimited; when the
   limit is reached, all invoices are validated and valid ones can be downloaded up to the limit. Please confirm or correct.
