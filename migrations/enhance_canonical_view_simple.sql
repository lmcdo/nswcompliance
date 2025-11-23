-- Drop and recreate VIEW with documents JOIN (no slow test queries)
DROP VIEW IF EXISTS regulatory_provisions_canonical CASCADE;

CREATE VIEW regulatory_provisions_canonical AS
SELECT
    rp.*,
    d.document_type,
    d.document_area,
    d.pdf_name,
    d.pdf_path
FROM regulatory_provisions rp
LEFT JOIN documents d ON rp.document_id = d.id
WHERE rp.is_canonical = TRUE;
