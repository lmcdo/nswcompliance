
-- Efficient Provision Mapping SQL Script
-- Generated for production deployment

-- Strategy 1: Document Title Mapping
UPDATE regulatory_provisions rp
SET zone = CASE
    WHEN d.pdf_name LIKE '%Low Density%' OR d.pdf_name LIKE '%4.1%' THEN 'R2'
    WHEN d.pdf_name LIKE '%Medium Density%' OR d.pdf_name LIKE '%4.2%' THEN 'R3'
    WHEN d.pdf_name LIKE '%High Density%' OR d.pdf_name LIKE '%4.3%' THEN 'R4'
    WHEN d.pdf_name LIKE '%Commercial%' OR d.pdf_name LIKE '%5.%' THEN 'B1'
    WHEN d.pdf_name LIKE '%Mixed Use%' THEN 'B4'
    WHEN d.pdf_name LIKE '%Industrial%' OR d.pdf_name LIKE '%6.%' THEN 'IN1'
    ELSE zone
END
FROM documents d
WHERE rp.document_id = d.id
AND rp.zone IS NULL;

-- Strategy 2: Document Inheritance
WITH zone_inheritance AS (
    SELECT document_id, MAX(zone) as inherited_zone
    FROM regulatory_provisions
    WHERE zone IS NOT NULL
    GROUP BY document_id
)
UPDATE regulatory_provisions
SET zone = zi.inherited_zone
FROM zone_inheritance zi
WHERE regulatory_provisions.document_id = zi.document_id
AND regulatory_provisions.zone IS NULL;

-- Strategy 3: Reference Pattern Mapping
UPDATE regulatory_provisions
SET zone = CASE
    WHEN ref_number LIKE '4.1%' THEN 'R2'
    WHEN ref_number LIKE '4.2%' THEN 'R3'
    WHEN ref_number LIKE '4.3%' THEN 'R4'
    WHEN ref_number LIKE '5.%' THEN 'B1'
    WHEN ref_number LIKE '6.%' THEN 'IN1'
    ELSE zone
END
WHERE zone IS NULL
AND ref_number IS NOT NULL;
