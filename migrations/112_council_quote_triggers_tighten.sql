-- 112: tighten migration 111's quote triggers (Sol cross-review, 2026-10-12).
--
-- prior-art-checked: replaces the two functions migration 111 created; no new objects.
--
-- 1. 111 kept a quote when an update changed the rule's text AND quote_checked_at together (the 079
--    pattern, so the writer's own update survives). The copier never changes provision_text,
--    source_chapter_key or source_council, so no update that changes them can be the copier:
--    any such change now clears the quote, whatever else it sets.
-- 2. 111 voided quotes on a new chapter PDF only for is_current rows. A non-current row keeping an
--    old PDF's quote would carry it back when set current again. Now every row of the chapter.

CREATE OR REPLACE FUNCTION regulatory_provisions_clear_quote() RETURNS trigger AS $$
BEGIN
    IF NEW.provision_text IS DISTINCT FROM OLD.provision_text
       OR NEW.source_chapter_key IS DISTINCT FROM OLD.source_chapter_key
       OR NEW.source_council IS DISTINCT FROM OLD.source_council THEN
        NEW.council_quote := NULL;
        NEW.quote_page := NULL;
        NEW.quote_source_path := NULL;
        NEW.quote_status := NULL;
        NEW.quote_reason := NULL;
        NEW.quote_checked_at := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION dcp_chapter_registry_void_quotes() RETURNS trigger AS $$
BEGIN
    IF NEW.r2_current_path IS DISTINCT FROM OLD.r2_current_path
       OR NEW.is_active IS DISTINCT FROM OLD.is_active THEN
        UPDATE regulatory_provisions
           SET council_quote = NULL, quote_page = NULL, quote_source_path = NULL,
               quote_status = NULL, quote_reason = NULL, quote_checked_at = NULL
         WHERE source_council = NEW.council AND source_chapter_key = NEW.chapter_key
           AND quote_status IS NOT NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
