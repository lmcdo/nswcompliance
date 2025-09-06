# PRP-K1: Foundation Data Infrastructure - SQLite to PostgreSQL Migration
## Database-Driven Compliance Engine Infrastructure for Inner West Planning System

**Document ID:** PRP-K1_FOUNDATION_DATA_INFRASTRUCTURE_DETAILED  
**Version:** 2.0  
**Date:** 2025-09-05  
**Technical Complexity:** High  
**Priority:** 1 (Foundation - Must Complete Before All Others)  
**Dependencies:** Existing nsw_planning.db (22K+ records), Python 3.11+, SQLite→PostgreSQL migration tools  
**Duration:** 2-3 weeks (160-240 developer hours)  
**Status:** Ready for Implementation - COMPREHENSIVE TECHNICAL SPECIFICATION

---

## Technical Architecture Overview

### System Components Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    DATA MIGRATION LAYER                    │
├─────────────────┬─────────────────┬─────────────────────────┤
│ SQLite Source   │ Migration ETL   │ Quality Validation      │
│ - nsw_planning  │ - Schema Map    │ - Data Integrity        │
│ - 22K+ Records  │ - Transform     │ - Cross-Reference       │
│ - Existing APIs │ - Load          │ - Business Rules        │
│ - Route Support │ - Verification  │ - Performance Testing   │
└─────────────────┴─────────────────┴─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            DUAL DATABASE ARCHITECTURE                     │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Development     │ Migration Layer │ Production Target       │
│ - SQLite 3.38+  │ - Data Sync     │ - PostgreSQL 14.9+     │
│ - Fast Queries  │ - Schema Sync   │ - Full Features         │
│ - Local Dev     │ - Validation    │ - JSONB, GIN Indexes   │
│ - Route Compat  │ - Rollback      │ - Advanced Constraints  │
└─────────────────┴─────────────────┴─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 ENHANCED API ACCESS LAYER                  │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Existing Routes │ New Queries     │ Performance Layer       │
│ - /property/*   │ - Domain Filter │ - Connection Pool       │
│ - /da/* APIs    │ - Cross-Ref     │ - Query Cache          │
│ - Frontend Compat │ - Analytics   │ - Monitoring           │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Technology Stack Specifications

**Database Platform:**
```
Development Phase (Immediate):
  ✓ SQLite 3.38+ (existing nsw_planning.db)
  ✓ 22,092+ verified regulatory provisions
  ✓ Compatible with existing API routes
  ✓ Fast development iteration
  ✓ Zero-downtime local development

Production Migration Target:
  → PostgreSQL 14.9+ (advanced enterprise features)
  → JSONB native support for complex metadata
  → GIN indexes for full-text search
  → UUID primary keys for distributed systems
  → Advanced constraints and triggers
  → Connection pooling with pgBouncer

Migration Strategy:
  • Automated SQLite→PostgreSQL pipeline
  • Schema transformation with data preservation
  • API compatibility layer during transition
  • Rollback capability to SQLite if needed
  • Zero data loss guarantee
```

**ETL Framework:**
- **Python 3.11+** (Enhanced error handling, performance optimizations)
- **Dependencies:** sqlite3 (built-in), psycopg2-binary 2.9+, SQLAlchemy 2.0+, pandas 2.0+
- **Migration Tools:** Custom migration scripts with transaction safety
- **Monitoring:** Performance comparison SQLite vs PostgreSQL

**Infrastructure Requirements:**
- **Development**: Existing SQLite database (validated working state)
- **Production**: PostgreSQL server with 8+ CPU cores, 32GB RAM
- **Network**: Secure database connections with TLS 1.3
- **Backup**: Point-in-time recovery for production PostgreSQL

---

## EXISTING DATABASE SCHEMA ANALYSIS

### Current SQLite Schema (nsw_planning.db)
```sql
-- =====================================================
-- EXISTING TABLES (22,092+ RECORDS VERIFIED)
-- =====================================================

-- Core regulatory data tables:
documents                    -- Document metadata and sources
regulatory_refs              -- Cross-references between provisions  
regulatory_provisions        -- Main compliance provisions (22K+ records)
regulatory_provisions_clean  -- Cleaned/processed provisions
contextual_guidance         -- Additional guidance and context
contextual_guidance_real    -- Verified contextual data

-- Knowledge graph and relationships:
kg_entities                 -- Knowledge graph entities
kg_relationships           -- Entity relationships
kg_relationships_from_refs -- Cross-reference relationships
kg_visual_elements         -- Visual content integration
kg_visual_clause_links     -- Links between clauses and visuals

-- Development controls and standards:
development_controls       -- Specific development requirements
quantitative_standards     -- Numerical requirements (setbacks, heights)
development_pathways       -- Development approval pathways

-- Visual and supporting data:
visual_elements           -- PDF visual content
visual_elements_real      -- Verified visual content
clause_relationships      -- Inter-clause dependencies

-- Override and special provisions:
sepp_lep_overrides       -- State/Local Environmental Plan overrides
regulatory_refs_core     -- Core regulatory references

-- Performance and caching:
query_cache              -- Query result caching
sqlite_sequence          -- SQLite auto-increment tracking
```

### Migration Schema Mapping (SQLite → PostgreSQL)

```sql
-- =====================================================
-- ENHANCED POSTGRESQL SCHEMA WITH MIGRATION MAPPING
-- =====================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Custom types for strong typing
CREATE TYPE council_area_type AS ENUM ('marrickville', 'leichhardt', 'ashfield', 'inner_west');
CREATE TYPE document_type_enum AS ENUM ('DCP', 'LEP', 'SEPP', 'SREP', 'EPI', 'MIXED');
CREATE TYPE verification_status_enum AS ENUM ('VERIFIED', 'PENDING', 'REJECTED', 'MIGRATED');
CREATE TYPE domain_classification_enum AS ENUM (
    'RESIDENTIAL_BUILDINGS', 
    'COMMERCIAL_BUILDINGS', 
    'INDUSTRIAL_BUILDINGS',
    'SIGNAGE_ADVERTISING', 
    'PARKING_TRANSPORT', 
    'HERITAGE_CONSERVATION', 
    'ENVIRONMENTAL_PROTECTION',
    'INFRASTRUCTURE_UTILITIES',
    'GENERAL_PROVISIONS'
);

-- MIGRATION MAPPING: regulatory_provisions (SQLite) → regulatory_provisions_v2 (PostgreSQL)
CREATE TABLE regulatory_provisions_v2 (
    -- Primary identification (enhanced from SQLite version)
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Source identification and lineage (mapped from SQLite)
    sqlite_source_id INTEGER, -- Original SQLite ID for traceability
    source_document_key TEXT NOT NULL,
    source_path TEXT,
    original_pdf_path TEXT,
    extraction_method TEXT DEFAULT 'existing_sqlite_migration',
    
    -- Council and document metadata (enhanced classification)
    council_area council_area_type NOT NULL,
    document_type document_type_enum NOT NULL,
    document_version TEXT,
    document_date DATE,
    section_number TEXT,
    section_title TEXT NOT NULL,
    subsection_number TEXT,
    clause_number TEXT,
    
    -- Hierarchical structure (new capabilities)
    parent_section_id UUID REFERENCES regulatory_provisions_v2(id),
    hierarchy_level INTEGER CHECK (hierarchy_level BETWEEN 1 AND 10),
    sort_order INTEGER,
    
    -- Content and classification (enhanced from SQLite)
    provision_text TEXT NOT NULL CHECK (length(provision_text) > 10),
    provision_text_tsvector TSVECTOR, -- Full-text search optimization
    provision_type TEXT,
    domain_classification domain_classification_enum NOT NULL,
    secondary_domains domain_classification_enum[],
    classification_confidence DECIMAL(5,4) DEFAULT 0.95,
    classification_method TEXT DEFAULT 'sqlite_migration',
    
    -- Regulatory semantics (from existing SQLite data)
    clause_reference TEXT,
    specific_requirements JSONB,
    measurements JSONB,
    applies_to TEXT,
    zone_applicability TEXT[],
    building_types TEXT[],
    
    -- Geographic scope (new capability)
    geographic_bounds GEOMETRY(POLYGON, 4326), -- PostGIS for spatial data
    address_applicability TEXT[],
    
    -- Legal and compliance metadata (enhanced)
    legal_authority TEXT DEFAULT 'Inner West Council',
    enforcement_mechanism TEXT,
    penalty_provisions TEXT,
    exemptions JSONB,
    related_provisions UUID[],
    
    -- Quality and verification (migration tracking)
    verification_status verification_status_enum DEFAULT 'MIGRATED',
    extraction_quality_score DECIMAL(5,4) DEFAULT 0.95,
    human_reviewed BOOLEAN DEFAULT FALSE,
    migration_verified BOOLEAN DEFAULT FALSE,
    migration_notes TEXT,
    
    -- Temporal validity
    effective_from DATE,
    effective_to DATE,
    superseded_by UUID REFERENCES regulatory_provisions_v2(id),
    
    -- Audit and versioning (enhanced tracking)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    migrated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'sqlite_migration_system',
    updated_by TEXT,
    data_version TEXT NOT NULL DEFAULT 'migration_v1',
    record_hash TEXT, -- For change detection
    
    -- Migration-specific constraints
    UNIQUE(sqlite_source_id), -- Ensure no duplicate migrations
    UNIQUE(source_document_key, section_number, clause_reference, data_version),
    CHECK (effective_from IS NULL OR effective_to IS NULL OR effective_from <= effective_to),
    CHECK (length(provision_text) <= 50000), -- Prevent excessive text
    CHECK (classification_confidence > 0.1 OR human_reviewed = TRUE)
);

-- MIGRATION MAPPING: quantitative_standards (SQLite) → enhanced table (PostgreSQL)
CREATE TABLE quantitative_standards_v2 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sqlite_source_id INTEGER UNIQUE, -- Original SQLite ID
    provision_id UUID REFERENCES regulatory_provisions_v2(id) ON DELETE CASCADE,
    
    -- Standard specifications (from existing data)
    standard_type TEXT NOT NULL, -- 'setback', 'height', 'fsr', 'lot_coverage'
    boundary_type TEXT, -- 'front', 'side', 'rear', 'general'
    minimum_value DECIMAL(10,3),
    maximum_value DECIMAL(10,3),
    unit_of_measure TEXT NOT NULL, -- 'meters', 'percent', 'ratio'
    
    -- Context and applicability (enhanced)
    zone_applicability TEXT[],
    building_types TEXT[],
    site_conditions JSONB, -- Slope, corner lot, etc.
    
    -- Legal backing
    clause_reference TEXT NOT NULL,
    legal_authority TEXT DEFAULT 'Inner West Council',
    confidence_score DECIMAL(5,4) DEFAULT 0.95,
    
    -- Audit
    migrated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (minimum_value IS NULL OR minimum_value >= 0),
    CHECK (maximum_value IS NULL OR maximum_value >= minimum_value),
    CHECK (confidence_score BETWEEN 0.1 AND 1.0)
);

-- MIGRATION MAPPING: development_controls (SQLite) → enhanced table (PostgreSQL)
CREATE TABLE development_controls_v2 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sqlite_source_id INTEGER UNIQUE,
    provision_id UUID REFERENCES regulatory_provisions_v2(id) ON DELETE CASCADE,
    
    -- Control specifications
    control_type TEXT NOT NULL,
    control_category domain_classification_enum NOT NULL,
    requirements JSONB NOT NULL,
    mandatory BOOLEAN DEFAULT TRUE,
    
    -- Context
    applies_to_zones TEXT[],
    applies_to_development_types TEXT[],
    site_specific_conditions JSONB,
    
    -- Cross-domain contamination prevention
    domain_verified BOOLEAN DEFAULT FALSE,
    contamination_check_passed BOOLEAN DEFAULT FALSE,
    
    -- Legal
    clause_reference TEXT NOT NULL,
    enforcement_level TEXT DEFAULT 'MANDATORY',
    
    -- Audit
    migrated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## COMPREHENSIVE MIGRATION PIPELINE

### Advanced Migration Architecture with Zero Data Loss

```python
#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Pipeline
======================================

Enterprise-grade migration system for Inner West planning compliance database.
Preserves all existing data while enhancing schema for production scalability.
"""

import asyncio
import logging
import sqlite3
import json
import hashlib
import psutil
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import psycopg2
from psycopg2.extras import execute_values, Json
import concurrent.futures
from contextlib import contextmanager
import backoff

@dataclass
class MigrationConfiguration:
    """Comprehensive migration configuration with validation"""
    
    # Database configurations
    sqlite_db_path: str = "./nsw_planning.db"
    postgresql_url: str  # Must be provided
    
    # Migration settings
    batch_size: int = 1000
    max_workers: int = 4
    enable_parallel_migration: bool = True
    
    # Data validation settings
    enable_data_validation: bool = True
    validation_sample_size: int = 1000
    acceptable_data_loss_percent: float = 0.0  # Zero tolerance
    
    # Performance settings
    connection_pool_size: int = 10
    max_overflow: int = 20
    migration_timeout_hours: int = 24
    
    # Backup and rollback
    create_backup: bool = True
    backup_directory: Path = Path("./migration_backups")
    enable_rollback: bool = True
    
    def __post_init__(self):
        """Validate configuration"""
        if not Path(self.sqlite_db_path).exists():
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_db_path}")
        
        if self.acceptable_data_loss_percent > 0.01:  # Max 0.01% loss
            raise ValueError("Data loss tolerance too high for production migration")

@dataclass
class MigrationMetrics:
    """Detailed migration metrics and monitoring"""
    
    # Record counts
    total_records: int = 0
    migrated_records: int = 0
    failed_records: int = 0
    validation_errors: int = 0
    
    # Performance metrics
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    peak_memory_mb: float = 0.0
    
    # Data integrity metrics
    source_record_hashes: Dict[str, str] = field(default_factory=dict)
    target_record_hashes: Dict[str, str] = field(default_factory=dict)
    data_integrity_score: float = 0.0
    
    # Table-specific metrics
    table_migration_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate migration success rate"""
        if self.total_records == 0:
            return 0.0
        return self.migrated_records / self.total_records
    
    @property
    def migration_duration_seconds(self) -> Optional[int]:
        """Calculate total migration duration"""
        if self.end_time and self.start_time:
            return int((self.end_time - self.start_time).total_seconds())
        return None

class EnterpriseMigrationPipeline:
    """
    Enterprise-grade SQLite to PostgreSQL migration pipeline.
    
    Features:
    - Zero data loss guarantee
    - Comprehensive validation and verification
    - Rollback capability
    - Performance monitoring
    - Schema enhancement during migration
    - API compatibility preservation
    """
    
    def __init__(self, config: MigrationConfiguration):
        self.config = config
        self.metrics = MigrationMetrics()
        self.migration_id = self._generate_migration_id()
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize database connections
        self._setup_database_connections()
        
        # Domain classification mapping for enhanced schema
        self.domain_mapping = self._initialize_domain_mapping()
    
    def _generate_migration_id(self) -> str:
        """Generate unique migration ID for tracking"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        hash_part = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"migration_{timestamp}_{hash_part}"
    
    def _setup_logging(self):
        """Configure comprehensive migration logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(migration_id)s] - %(message)s',
            handlers=[
                logging.FileHandler(f'migration_{self.migration_id}.log'),
                logging.StreamHandler()
            ]
        )
        
        # Add migration_id to all log records
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.migration_id = self.migration_id
            return record
        logging.setLogRecordFactory(record_factory)
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_database_connections(self):
        """Initialize both SQLite and PostgreSQL connections"""
        # SQLite connection (source)
        self.sqlite_conn = sqlite3.connect(
            self.config.sqlite_db_path,
            timeout=30.0,
            isolation_level=None  # Autocommit mode for read operations
        )
        self.sqlite_conn.row_factory = sqlite3.Row  # Enable column access by name
        
        # PostgreSQL connection (target)
        self.pg_engine = create_engine(
            self.config.postgresql_url,
            poolclass=QueuePool,
            pool_size=self.config.connection_pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=30,
            pool_pre_ping=True,
            echo=False  # Set to True for SQL debugging
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.pg_engine)
    
    def _initialize_domain_mapping(self) -> Dict[str, str]:
        """Initialize domain classification mapping for cross-contamination prevention"""
        return {
            'signage': 'SIGNAGE_ADVERTISING',
            'advertising': 'SIGNAGE_ADVERTISING', 
            'signs': 'SIGNAGE_ADVERTISING',
            'residential': 'RESIDENTIAL_BUILDINGS',
            'dwelling': 'RESIDENTIAL_BUILDINGS',
            'house': 'RESIDENTIAL_BUILDINGS',
            'apartment': 'RESIDENTIAL_BUILDINGS',
            'parking': 'PARKING_TRANSPORT',
            'vehicle': 'PARKING_TRANSPORT',
            'commercial': 'COMMERCIAL_BUILDINGS',
            'retail': 'COMMERCIAL_BUILDINGS',
            'industrial': 'INDUSTRIAL_BUILDINGS',
            'heritage': 'HERITAGE_CONSERVATION',
            'environment': 'ENVIRONMENTAL_PROTECTION',
            'infrastructure': 'INFRASTRUCTURE_UTILITIES'
        }
    
    async def execute_complete_migration(self) -> 'MigrationResult':
        """
        Execute complete migration pipeline with comprehensive validation
        
        Migration Stages:
        1. Pre-migration validation and backup
        2. Schema creation and enhancement
        3. Data migration with transformation
        4. Post-migration validation and verification
        5. API compatibility testing
        6. Performance optimization
        """
        
        self.logger.info(f"Starting enterprise migration pipeline - ID: {self.migration_id}")
        
        try:
            # Stage 1: Pre-migration validation and backup
            self.logger.info("Stage 1: Pre-migration validation and backup")
            pre_validation_result = await self._execute_pre_migration_validation()
            if not pre_validation_result.success:
                raise MigrationException(f"Pre-migration validation failed: {pre_validation_result.errors}")
            
            # Create backup if enabled
            if self.config.create_backup:
                backup_result = await self._create_migration_backup()
                self.logger.info(f"Backup created: {backup_result.backup_path}")
            
            # Stage 2: Schema creation and enhancement
            self.logger.info("Stage 2: PostgreSQL schema creation and enhancement")
            schema_result = await self._create_enhanced_postgresql_schema()
            if not schema_result.success:
                raise MigrationException(f"Schema creation failed: {schema_result.errors}")
            
            # Stage 3: Data migration with transformation
            self.logger.info("Stage 3: Data migration with transformation and enhancement")
            migration_result = await self._execute_data_migration_with_enhancement()
            if migration_result.success_rate < (1.0 - self.config.acceptable_data_loss_percent):
                raise MigrationException(f"Migration success rate {migration_result.success_rate:.4%} below acceptable threshold")
            
            # Stage 4: Post-migration validation and verification
            self.logger.info("Stage 4: Post-migration validation and verification")
            post_validation_result = await self._execute_comprehensive_post_migration_validation()
            if not post_validation_result.success:
                if self.config.enable_rollback:
                    await self._execute_rollback()
                raise MigrationException(f"Post-migration validation failed: {post_validation_result.critical_failures}")
            
            # Stage 5: API compatibility testing
            self.logger.info("Stage 5: API compatibility testing")
            api_test_result = await self._test_api_compatibility()
            if not api_test_result.all_tests_passed:
                self.logger.warning("Some API compatibility issues detected - manual review required")
            
            # Stage 6: Performance optimization
            self.logger.info("Stage 6: Performance optimization and indexing")
            await self._optimize_postgresql_performance()
            
            # Finalize metrics and generate comprehensive report
            self.metrics.end_time = datetime.now(timezone.utc)
            final_report = await self._generate_migration_report()
            
            self.logger.info(f"Migration completed successfully - Duration: {self.metrics.migration_duration_seconds}s")
            self.logger.info(f"Records migrated: {self.metrics.migrated_records:,}/{self.metrics.total_records:,}")
            self.logger.info(f"Data integrity score: {self.metrics.data_integrity_score:.6f}")
            
            return MigrationResult(
                success=True,
                migration_id=self.migration_id,
                metrics=self.metrics,
                report=final_report,
                postgresql_ready=True,
                api_compatible=api_test_result.all_tests_passed
            )
            
        except Exception as e:
            self.logger.error(f"Migration pipeline failed: {str(e)}", exc_info=True)
            await self._handle_migration_failure(e)
            raise
        
        finally:
            # Ensure cleanup always happens
            await self._cleanup_connections()
    
    async def _execute_pre_migration_validation(self) -> 'ValidationResult':
        """Execute comprehensive pre-migration validation"""
        
        self.logger.info("Executing pre-migration validation checks")
        
        validation_results = []
        
        # Check 1: SQLite database integrity and accessibility
        sqlite_check = await self._validate_sqlite_database()
        validation_results.append(("sqlite_integrity", sqlite_check))
        
        # Check 2: PostgreSQL connectivity and permissions
        postgresql_check = await self._validate_postgresql_connectivity()
        validation_results.append(("postgresql_connectivity", postgresql_check))
        
        # Check 3: Data volume and expected migration time
        volume_check = await self._validate_migration_feasibility()
        validation_results.append(("migration_feasibility", volume_check))
        
        # Check 4: System resources
        resource_check = await self._validate_system_resources()
        validation_results.append(("system_resources", resource_check))
        
        # Evaluate overall validation status
        failed_checks = [name for name, result in validation_results if not result.success]
        overall_success = len(failed_checks) == 0
        
        return ValidationResult(
            success=overall_success,
            checks=dict(validation_results),
            errors=failed_checks,
            warnings=[name for name, result in validation_results if result.warnings]
        )
    
    async def _execute_data_migration_with_enhancement(self) -> 'DataMigrationResult':
        """Execute data migration with schema enhancements and domain classification"""
        
        self.logger.info("Starting enhanced data migration")
        
        # Define migration plan for all tables
        migration_plan = await self._create_migration_plan()
        
        # Track progress
        total_tables = len(migration_plan)
        completed_tables = 0
        
        # Execute table migrations in dependency order
        for table_name, migration_config in migration_plan.items():
            self.logger.info(f"Migrating table: {table_name} ({completed_tables + 1}/{total_tables})")
            
            try:
                # Execute table-specific migration
                table_result = await self._migrate_table_with_enhancement(table_name, migration_config)
                
                # Update metrics
                self.metrics.table_migration_status[table_name] = {
                    'success': table_result.success,
                    'records_migrated': table_result.records_migrated,
                    'enhancements_applied': table_result.enhancements_applied,
                    'validation_passed': table_result.validation_passed
                }
                
                if table_result.success:
                    self.metrics.migrated_records += table_result.records_migrated
                    completed_tables += 1
                    self.logger.info(f"Successfully migrated {table_name}: {table_result.records_migrated} records")
                else:
                    self.metrics.failed_records += table_result.failed_records
                    self.logger.error(f"Failed to migrate {table_name}: {table_result.errors}")
                    
            except Exception as e:
                self.logger.error(f"Unexpected error migrating {table_name}: {str(e)}", exc_info=True)
                self.metrics.failed_records += 1
        
        # Calculate final success metrics
        success_rate = completed_tables / total_tables if total_tables > 0 else 0.0
        
        return DataMigrationResult(
            success_rate=success_rate,
            total_records=self.metrics.total_records,
            migrated_records=self.metrics.migrated_records,
            failed_records=self.metrics.failed_records,
            table_results=self.metrics.table_migration_status
        )
    
    async def _migrate_table_with_enhancement(self, table_name: str, migration_config: Dict[str, Any]) -> 'TableMigrationResult':
        """Migrate individual table with enhancements and domain classification"""
        
        # Get source data from SQLite
        source_query = migration_config['source_query']
        target_table = migration_config['target_table']
        enhancements = migration_config.get('enhancements', [])
        
        # Fetch source data
        cursor = self.sqlite_conn.cursor()
        cursor.execute(source_query)
        source_records = cursor.fetchall()
        
        if not source_records:
            return TableMigrationResult(
                success=True,
                records_migrated=0,
                failed_records=0,
                enhancements_applied=[],
                validation_passed=True
            )
        
        # Apply enhancements during migration
        enhanced_records = []
        enhancements_applied = []
        
        for record in source_records:
            enhanced_record = dict(record)  # Convert sqlite3.Row to dict
            
            # Apply table-specific enhancements
            for enhancement in enhancements:
                if enhancement['type'] == 'domain_classification':
                    domain = await self._classify_provision_domain(enhanced_record)
                    enhanced_record['domain_classification'] = domain
                    enhancements_applied.append(f'domain_classification:{domain}')
                
                elif enhancement['type'] == 'uuid_generation':
                    import uuid
                    enhanced_record['id'] = str(uuid.uuid4())
                    enhancements_applied.append('uuid_generation')
                
                elif enhancement['type'] == 'jsonb_conversion':
                    field_name = enhancement['field']
                    if field_name in enhanced_record and enhanced_record[field_name]:
                        try:
                            # Convert string to proper JSONB format
                            if isinstance(enhanced_record[field_name], str):
                                enhanced_record[field_name] = json.loads(enhanced_record[field_name])
                            enhancements_applied.append(f'jsonb_conversion:{field_name}')
                        except (json.JSONDecodeError, TypeError):
                            # Keep original value if JSON parsing fails
                            pass
                
                elif enhancement['type'] == 'migration_metadata':
                    enhanced_record['migrated_at'] = datetime.now(timezone.utc)
                    enhanced_record['sqlite_source_id'] = enhanced_record.get('id')
                    enhanced_record['migration_id'] = self.migration_id
                    enhancements_applied.append('migration_metadata')
            
            enhanced_records.append(enhanced_record)
        
        # Insert enhanced records into PostgreSQL
        try:
            with self.get_pg_session() as session:
                # Use batch insert for performance
                insert_query = self._build_insert_query(target_table, enhanced_records[0].keys())
                
                # Execute batch insert
                session.execute(text(insert_query), enhanced_records)
                session.commit()
                
                records_migrated = len(enhanced_records)
                
                # Validate migration
                validation_passed = await self._validate_table_migration(table_name, target_table, records_migrated)
                
                return TableMigrationResult(
                    success=True,
                    records_migrated=records_migrated,
                    failed_records=0,
                    enhancements_applied=list(set(enhancements_applied)),
                    validation_passed=validation_passed
                )
                
        except Exception as e:
            self.logger.error(f"Error inserting records into {target_table}: {str(e)}")
            return TableMigrationResult(
                success=False,
                records_migrated=0,
                failed_records=len(enhanced_records),
                enhancements_applied=[],
                validation_passed=False,
                errors=[str(e)]
            )
    
    async def _classify_provision_domain(self, record: Dict[str, Any]) -> str:
        """Classify provision domain to prevent cross-domain contamination"""
        
        # Get text fields for analysis
        provision_text = record.get('provision_text', '').lower()
        section_title = record.get('section_title', '').lower()
        clause_reference = record.get('clause_reference', '').lower()
        
        # Combined text for analysis
        combined_text = f"{provision_text} {section_title} {clause_reference}"
        
        # Domain classification using keyword analysis
        domain_scores = {}
        
        for keyword, domain in self.domain_mapping.items():
            if keyword in combined_text:
                if domain not in domain_scores:
                    domain_scores[domain] = 0
                domain_scores[domain] += combined_text.count(keyword)
        
        # Return highest scoring domain, default to GENERAL_PROVISIONS
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        else:
            return 'GENERAL_PROVISIONS'
    
    @contextmanager
    def get_pg_session(self):
        """Context manager for PostgreSQL sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def _create_migration_plan(self) -> Dict[str, Dict[str, Any]]:
        """Create comprehensive migration plan for all tables"""
        
        return {
            'regulatory_provisions': {
                'source_query': '''
                    SELECT id, source_document_key, provision_text, section_title,
                           section_number, clause_reference, council_area,
                           document_type, applies_to, measurements, created_at
                    FROM regulatory_provisions
                    WHERE provision_text IS NOT NULL AND provision_text != ''
                ''',
                'target_table': 'regulatory_provisions_v2',
                'enhancements': [
                    {'type': 'uuid_generation'},
                    {'type': 'domain_classification'},
                    {'type': 'jsonb_conversion', 'field': 'measurements'},
                    {'type': 'migration_metadata'}
                ]
            },
            
            'quantitative_standards': {
                'source_query': '''
                    SELECT id, provision_id, standard_type, boundary_type,
                           minimum_value, maximum_value, unit_of_measure,
                           clause_reference, confidence_score
                    FROM quantitative_standards
                    WHERE standard_type IS NOT NULL
                ''',
                'target_table': 'quantitative_standards_v2',
                'enhancements': [
                    {'type': 'uuid_generation'},
                    {'type': 'migration_metadata'}
                ]
            },
            
            'development_controls': {
                'source_query': '''
                    SELECT id, provision_id, control_type, requirements,
                           clause_reference, applies_to_zones
                    FROM development_controls
                    WHERE control_type IS NOT NULL
                ''',
                'target_table': 'development_controls_v2',
                'enhancements': [
                    {'type': 'uuid_generation'},
                    {'type': 'jsonb_conversion', 'field': 'requirements'},
                    {'type': 'migration_metadata'}
                ]
            }
            
            # Add additional tables as needed...
        }
    
    def _build_insert_query(self, table_name: str, columns: List[str]) -> str:
        """Build parameterized insert query for PostgreSQL"""
        
        column_list = ', '.join(columns)
        value_placeholders = ', '.join(f':{col}' for col in columns)
        
        return f'''
            INSERT INTO {table_name} ({column_list})
            VALUES ({value_placeholders})
        '''

# Supporting classes for migration pipeline
@dataclass
class ValidationResult:
    success: bool
    checks: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass  
class TableMigrationResult:
    success: bool
    records_migrated: int
    failed_records: int
    enhancements_applied: List[str]
    validation_passed: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class DataMigrationResult:
    success_rate: float
    total_records: int
    migrated_records: int
    failed_records: int
    table_results: Dict[str, Dict[str, Any]]

@dataclass
class MigrationResult:
    success: bool
    migration_id: str
    metrics: MigrationMetrics
    report: Dict[str, Any]
    postgresql_ready: bool
    api_compatible: bool

class MigrationException(Exception):
    """Custom exception for migration failures"""
    pass
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Migration Infrastructure (Week 1)
**Technical Tasks:**
- Set up PostgreSQL 14+ server with required extensions
- Implement migration pipeline with comprehensive validation
- Create backup and rollback procedures
- Test migration with subset of data (1000 records)

**Validation Criteria:**
- Migration pipeline achieves 99.99%+ success rate on test data
- All data integrity checks pass with zero discrepancies  
- Rollback procedure tested and functional
- Performance benchmarks established

### Phase 2: Full Data Migration (Week 2)
**Technical Tasks:**
- Execute complete migration of 22K+ records
- Apply domain classification to prevent cross-contamination
- Validate all existing API routes work with PostgreSQL
- Performance optimization and indexing

**Validation Criteria:**
- All 22,092+ records migrated successfully
- Zero data loss or corruption
- API response times maintain <100ms performance
- Cross-domain contamination eliminated (signage/residential separation)

### Phase 3: Production Deployment (Week 3)  
**Technical Tasks:**
- Production PostgreSQL deployment and configuration
- Connection pooling and monitoring setup
- API compatibility layer and gradual migration
- Documentation and operational procedures

**Validation Criteria:**
- Production deployment successful with zero downtime
- All existing functionality preserved
- Enhanced features available (domain filtering, advanced queries)
- Complete documentation and runbooks

---

## SUCCESS METRICS

### Migration Success Criteria
- **Data Integrity**: 100% record preservation with checksums verified
- **API Compatibility**: All existing routes functional post-migration  
- **Performance**: Query response times <100ms (maintained or improved)
- **Domain Separation**: Zero cross-domain contamination (signage ≠ residential)
- **Rollback Capability**: Complete rollback to SQLite within 1 hour if needed

### Production Readiness Metrics
- **Database Performance**: <50ms for 95% of regulatory provision lookups
- **Concurrent Users**: Handle 100+ simultaneous connections
- **Data Quality**: Cross-domain contamination detection accuracy >99.5%
- **System Reliability**: 99.9% uptime with comprehensive monitoring
- **Operational Excellence**: Complete migration documentation and procedures

This comprehensive PRP provides the detailed technical specification needed to migrate the existing SQLite database to PostgreSQL while preserving all functionality and eliminating the signage contamination issues through enhanced domain classification.