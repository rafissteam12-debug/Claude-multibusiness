-- AVV (Auftragsverarbeitungsvertrag) acceptance per user: asked before the first upload and again when the version
-- changes. Exact texts: app/legal_texts/avv-<version>.txt
ALTER TABLE users ADD COLUMN avv_version TEXT;
ALTER TABLE users ADD COLUMN avv_accepted_at REAL;
