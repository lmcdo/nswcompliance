-- PostgreSQL Database Backup
-- Database: nsw_planning_corrected
-- Created: 2025-09-24 12:44:48.833331
-- Method: Python manual backup


-- Table: clause_relationships
DROP TABLE IF EXISTS "clause_relationships" CASCADE;
CREATE TABLE "clause_relationships" (
  "id" integer NOT NULL DEFAULT nextval('clause_relationships_id_seq'::regclass),
  "parent_provision_id" integer,
  "child_provision_id" integer,
  "relationship_type" text,
  "confidence_score" numeric DEFAULT 1.0,
  "langextract_source" boolean DEFAULT true
);

