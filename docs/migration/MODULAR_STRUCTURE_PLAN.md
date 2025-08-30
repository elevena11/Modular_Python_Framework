# Semantic Analyzer Modular Structure Plan

## Overview

This document defines the complete module structure for rebuilding the Semantic Document Analyzer using the modular framework. Each module follows the framework's standardized patterns with clear boundaries and dependencies.

## Framework Structure

```
semantic_document_analyzer/
├── app.py                          # Main application (framework standard)
├── setup_db.py                     # Database initialization
├── config.json                     # Application configuration
├── requirements.txt                # Python dependencies
├── CLAUDE.md                       # AI development guidelines
├── modules/
│   ├── core/                       # Core framework modules (copied from framework)
│   │   ├── database/              # Database management
│   │   ├── settings/              # Configuration management
│   │   ├── error_handler/         # Error handling and logging
│   │   └── global/                # Framework standards
│   └── standard/                   # Application-specific modules
│       ├── semantic_core/         # Document storage and metadata
│       ├── vector_operations/     # ChromaDB and embeddings
│       ├── document_processing/   # File parsing and content extraction
│       ├── cli_interface/         # CLI command implementations
│       ├── cross_reference/       # Document relationship analysis
│       ├── clustering/            # Document grouping and themes
│       ├── obsidian_integration/  # Obsidian output generation
│       └── incremental_processing/ # Change detection and updates
├── tools/                          # Development tools (from framework)
├── ui/                            # Web interface (future)
├── data/
│   ├── database/                  # SQLite databases
│   ├── chromadb/                  # ChromaDB storage
│   ├── settings.json              # Framework settings
│   └── logs/                      # Application logs
└── docs/                          # Documentation
```

## Core Modules (Framework)

### modules/core/database/
- **Purpose**: SQLite database management and utilities
- **Source**: Copied from python_modular_framework/modules/core/database/
- **Customization**: None - use framework standard

### modules/core/settings/  
- **Purpose**: Configuration management with validation
- **Source**: Copied from python_modular_framework/modules/core/settings/
- **Customization**: None - use framework standard

### modules/core/error_handler/
- **Purpose**: Standardized error handling and logging
- **Source**: Copied from python_modular_framework/modules/core/error_handler/
- **Customization**: None - use framework standard

### modules/core/global/
- **Purpose**: Framework standards and utilities  
- **Source**: Copied from python_modular_framework/modules/core/global/
- **Customization**: None - use framework standard

## Application Modules (Standard)

### 1. modules/standard/semantic_core/

**Purpose**: Core document storage and metadata management

#### Files Structure
```
semantic_core/
├── manifest.json           # Module metadata and dependencies
├── api.py                 # Module initialization and API endpoints
├── services.py            # Core business logic
├── module_settings.py     # Configuration schema
├── database.py           # Database operations
├── db_models.py          # SQLAlchemy table definitions
├── api_schemas.py        # Pydantic request/response models
└── utils.py              # Helper functions
```

#### Database Schema (semantic_core.db)
```sql
-- Documents table - core document registry
CREATE TABLE documents (
    content_hash TEXT PRIMARY KEY,      -- SHA256 hash of content
    filename TEXT NOT NULL UNIQUE,     -- Original filename
    relative_path TEXT NOT NULL,       -- Path relative to source
    absolute_path TEXT NOT NULL,       -- Full filesystem path
    file_size INTEGER NOT NULL,        -- File size in bytes
    word_count INTEGER NOT NULL,       -- Total word count
    category TEXT,                     -- Document category/theme
    last_modified TIMESTAMP NOT NULL,  -- File modification time
    processed_at TIMESTAMP NOT NULL,   -- When document was processed
    content_preview TEXT,              -- First 200 characters
    metadata JSON                      -- Additional metadata as JSON
);

-- Document changes tracking
CREATE TABLE document_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL,
    change_type TEXT NOT NULL,         -- 'added', 'modified', 'deleted'
    detected_at TIMESTAMP NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (content_hash) REFERENCES documents(content_hash)
);

-- Content extraction cache  
CREATE TABLE content_cache (
    content_hash TEXT PRIMARY KEY,
    raw_content TEXT NOT NULL,        -- Original markdown content
    processed_content TEXT NOT NULL,  -- Cleaned content for analysis
    extraction_method TEXT NOT NULL,  -- How content was extracted
    extracted_at TIMESTAMP NOT NULL,
    FOREIGN KEY (content_hash) REFERENCES documents(content_hash)
);
```

#### Key Services
- **DocumentRegistryService**: Document CRUD operations
- **ContentHashService**: SHA256 hashing and validation  
- **MetadataService**: Document metadata extraction and storage
- **ChangeTrackingService**: File modification detection

#### API Endpoints
- `POST /documents/register` - Register new document
- `GET /documents/{content_hash}` - Get document by hash
- `GET /documents/` - List all documents with filtering
- `PUT /documents/{content_hash}` - Update document metadata
- `DELETE /documents/{content_hash}` - Remove document

#### Dependencies
- None (core module)

---

### 2. modules/standard/vector_operations/

**Purpose**: ChromaDB embeddings and similarity operations

#### Files Structure
```
vector_operations/
├── manifest.json
├── api.py
├── services.py
├── module_settings.py
├── chromadb_manager.py    # ChromaDB operations
├── embedding_service.py   # Embedding generation
├── similarity_service.py  # Similarity calculations
├── api_schemas.py
└── utils.py
```

#### ChromaDB Collections
- **documents**: Main document embeddings
  - IDs: content_hash values
  - Embeddings: 1024-dimension vectors (mixedbread-ai model)
  - Metadata: filename, category, word_count

#### Key Services
- **EmbeddingService**: Generate embeddings using mixedbread-ai model
- **ChromaDBService**: ChromaDB collection management
- **SimilarityService**: Document similarity calculations
- **VectorIndexService**: Efficient vector search operations

#### API Endpoints
- `POST /vectors/generate` - Generate embeddings for content
- `POST /vectors/search/similar` - Find similar documents
- `POST /vectors/search/concept` - Search by concept/text
- `GET /vectors/stats` - Vector database statistics

#### Dependencies
- semantic_core (document registry)

---

### 3. modules/standard/document_processing/

**Purpose**: File parsing and content extraction

#### Files Structure
```
document_processing/
├── manifest.json
├── api.py
├── services.py
├── module_settings.py
├── parsers/
│   ├── markdown_parser.py    # Markdown file parsing
│   ├── frontmatter_parser.py # YAML frontmatter extraction
│   └── content_cleaner.py    # Content cleaning and preparation
├── database.py
├── db_models.py
├── api_schemas.py
└── utils.py
```

#### Database Schema (document_processing.db)
```sql
-- Processing jobs tracking
CREATE TABLE processing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,            -- 'full_scan', 'incremental', 'single_doc'
    status TEXT NOT NULL,              -- 'queued', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    documents_processed INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,
    error_details TEXT,
    settings JSON                      -- Job-specific settings
);

-- File parsing results
CREATE TABLE parsing_results (
    content_hash TEXT PRIMARY KEY,
    parser_version TEXT NOT NULL,
    frontmatter JSON,                  -- Extracted YAML frontmatter
    sections JSON,                     -- Document sections/headings
    links JSON,                        -- Internal and external links
    parsed_at TIMESTAMP NOT NULL,
    FOREIGN KEY (content_hash) REFERENCES documents(content_hash)
);

-- Processing errors
CREATE TABLE processing_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    occurred_at TIMESTAMP NOT NULL,
    resolved BOOLEAN DEFAULT FALSE
);
```

#### Key Services
- **FileProcessingService**: Orchestrate document processing pipeline
- **MarkdownParserService**: Parse markdown files and extract structure
- **ContentExtractionService**: Extract and clean content for analysis
- **BatchProcessingService**: Handle bulk document processing

#### API Endpoints
- `POST /processing/process` - Process single document
- `POST /processing/batch` - Start batch processing job
- `GET /processing/status/{job_id}` - Get processing job status
- `GET /processing/errors` - List processing errors

#### Dependencies
- semantic_core (document registration)

---

### 4. modules/standard/cli_interface/

**Purpose**: analyze.py command implementations and CLI interface

#### Files Structure
```
cli_interface/
├── manifest.json
├── api.py
├── services.py
├── module_settings.py
├── commands/
│   ├── status_command.py      # System status command
│   ├── similarity_command.py  # Similar document search
│   ├── concept_command.py     # Concept-based search
│   ├── analyze_command.py     # Full analysis pipeline
│   ├── cluster_command.py     # Clustering operations
│   └── query_command.py       # SQL query interface
├── formatters/
│   ├── json_formatter.py      # JSON output formatting
│   ├── table_formatter.py     # Tabular output formatting
│   └── file_formatter.py      # File output handling
├── database.py
├── db_models.py
├── api_schemas.py
└── utils.py
```

#### Database Schema (cli_interface.db)
```sql
-- CLI command history
CREATE TABLE command_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,         -- Session identifier
    command TEXT NOT NULL,            -- Full command string
    arguments JSON,                   -- Parsed command arguments
    executed_at TIMESTAMP NOT NULL,
    execution_time REAL,              -- Execution time in seconds
    status TEXT NOT NULL,             -- 'success', 'error', 'timeout'
    output_size INTEGER,              -- Size of output in bytes
    error_message TEXT
);

-- User sessions
CREATE TABLE cli_sessions (
    session_id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    command_count INTEGER DEFAULT 0,
    user_context JSON                 -- Session-specific context
);

-- Output caching for performance
CREATE TABLE output_cache (
    cache_key TEXT PRIMARY KEY,       -- Hash of command + arguments
    command TEXT NOT NULL,
    output_data TEXT NOT NULL,        -- Cached output
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0
);
```

#### Key Services
- **CLICommandService**: Command routing and execution
- **OutputFormattingService**: Format results for different output types
- **SessionService**: Manage CLI sessions and history
- **CacheService**: Cache frequent command results for performance

#### API Endpoints
- `POST /cli/execute` - Execute CLI command programmatically
- `GET /cli/history/{session_id}` - Get command history
- `GET /cli/sessions` - List active sessions
- `DELETE /cli/cache` - Clear output cache

#### Dependencies
- semantic_core (document data)
- vector_operations (similarity/concept search)
- document_processing (analysis pipeline)

---

### 5. modules/standard/cross_reference/

**Purpose**: Document relationship analysis and cross-reference detection

#### Files Structure
```
cross_reference/
├── manifest.json
├── api.py
├── services.py
├── module_settings.py
├── analyzers/
│   ├── concept_analyzer.py    # Shared concept detection
│   ├── link_analyzer.py       # Internal link analysis
│   └── theme_analyzer.py      # Thematic relationship analysis
├── database.py
├── db_models.py
├── api_schemas.py
└── utils.py
```

#### Database Schema (cross_reference.db)
```sql
-- Document relationships
CREATE TABLE document_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_hash TEXT NOT NULL,
    target_hash TEXT NOT NULL,
    relationship_type TEXT NOT NULL,   -- 'similar', 'references', 'concept_overlap'
    strength REAL NOT NULL,            -- Relationship strength (0.0-1.0)
    discovered_at TIMESTAMP NOT NULL,
    validated BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (source_hash) REFERENCES documents(content_hash),
    FOREIGN KEY (target_hash) REFERENCES documents(content_hash),
    UNIQUE(source_hash, target_hash, relationship_type)
);

-- Shared concepts between documents
CREATE TABLE shared_concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_text TEXT NOT NULL,
    concept_type TEXT NOT NULL,        -- 'term', 'phrase', 'theme'
    significance REAL NOT NULL,        -- Concept importance (0.0-1.0)
    first_seen TIMESTAMP NOT NULL,
    usage_count INTEGER DEFAULT 1
);

-- Document-concept associations
CREATE TABLE document_concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL,
    concept_id INTEGER NOT NULL,
    frequency INTEGER NOT NULL,        -- How often concept appears
    context TEXT,                      -- Context where concept appears
    FOREIGN KEY (content_hash) REFERENCES documents(content_hash),
    FOREIGN KEY (concept_id) REFERENCES shared_concepts(id),
    UNIQUE(content_hash, concept_id)
);

-- Cross-reference networks
CREATE TABLE reference_networks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_name TEXT NOT NULL,
    description TEXT,
    document_count INTEGER NOT NULL,
    relationship_count INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    last_updated TIMESTAMP NOT NULL
);
```

#### Key Services
- **RelationshipAnalysisService**: Detect and analyze document relationships
- **ConceptExtractionService**: Extract and index shared concepts
- **NetworkAnalysisService**: Analyze cross-reference networks
- **ValidationService**: Validate and score relationship quality

#### API Endpoints
- `POST /cross-ref/analyze` - Analyze cross-references for document(s)
- `GET /cross-ref/relationships/{content_hash}` - Get document relationships
- `GET /cross-ref/concepts` - List all concepts with usage statistics
- `GET /cross-ref/networks` - Get cross-reference network analysis

#### Dependencies
- semantic_core (document data)
- vector_operations (concept similarity)

---

### 6. modules/standard/clustering/

**Purpose**: Document grouping and theme detection

#### Files Structure
```
clustering/
├── manifest.json
├── api.py
├── services.py
├── module_settings.py
├── algorithms/
│   ├── kmeans_clustering.py   # K-means clustering implementation
│   ├── hierarchical_clustering.py  # Hierarchical clustering
│   └── adaptive_clustering.py     # Adaptive clustering
├── database.py
├── db_models.py
├── api_schemas.py
└── utils.py
```

#### Database Schema (clustering.db)
```sql
-- Clustering analyses
CREATE TABLE cluster_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_name TEXT NOT NULL,
    algorithm TEXT NOT NULL,          -- 'kmeans', 'hierarchical', 'adaptive'
    parameters JSON NOT NULL,         -- Algorithm parameters
    document_count INTEGER NOT NULL,
    cluster_count INTEGER NOT NULL,
    silhouette_score REAL,            -- Clustering quality metric
    calinski_harabasz_score REAL,     -- Another quality metric
    created_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT FALSE   -- Current active clustering
);

-- Cluster definitions
CREATE TABLE clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    cluster_number INTEGER NOT NULL,
    cluster_name TEXT,                -- Human-readable cluster name
    theme_description TEXT,           -- What this cluster represents
    document_count INTEGER NOT NULL,
    centroid_vector BLOB,             -- Cluster centroid (serialized)
    quality_score REAL,               -- Individual cluster quality
    FOREIGN KEY (analysis_id) REFERENCES cluster_analyses(id),
    UNIQUE(analysis_id, cluster_number)
);

-- Document cluster assignments
CREATE TABLE cluster_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    cluster_id INTEGER NOT NULL,
    distance_to_centroid REAL NOT NULL,
    assignment_confidence REAL NOT NULL,  -- How confident the assignment is
    assigned_at TIMESTAMP NOT NULL,
    FOREIGN KEY (analysis_id) REFERENCES cluster_analyses(id),
    FOREIGN KEY (content_hash) REFERENCES documents(content_hash),
    FOREIGN KEY (cluster_id) REFERENCES clusters(id),
    UNIQUE(analysis_id, content_hash)
);

-- Cluster themes and categories
CREATE TABLE cluster_themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER NOT NULL,
    theme_name TEXT NOT NULL,
    theme_keywords JSON,              -- Key terms for this theme
    vef_category TEXT,                -- VEF Framework category
    confidence REAL NOT NULL,         -- Theme detection confidence
    FOREIGN KEY (cluster_id) REFERENCES clusters(id)
);
```

#### Key Services
- **ClusteringService**: Execute clustering algorithms
- **ThemeDetectionService**: Detect and categorize cluster themes
- **ClusterAnalysisService**: Analyze clustering quality and results
- **AssignmentService**: Assign documents to clusters

#### API Endpoints
- `POST /clustering/analyze` - Run clustering analysis
- `GET /clustering/results/{analysis_id}` - Get clustering results
- `GET /clustering/themes` - List detected themes
- `PUT /clustering/activate/{analysis_id}` - Set active clustering

#### Dependencies
- semantic_core (document data)
- vector_operations (document embeddings)

---

### 7. modules/standard/obsidian_integration/

**Purpose**: Obsidian-compatible output generation

#### Files Structure
```
obsidian_integration/
├── manifest.json
├── api.py
├── services.py
├── module_settings.py
├── generators/
│   ├── wikilink_generator.py  # Generate [[wikilinks]]
│   ├── index_generator.py     # Create index files
│   └── vault_organizer.py     # Organize vault structure
├── templates/
│   ├── index_template.md      # Template for index files
│   ├── cluster_template.md    # Template for cluster pages
│   └── network_template.md    # Template for network views
├── database.py
├── db_models.py
├── api_schemas.py
└── utils.py
```

#### Database Schema (obsidian_integration.db)
```sql
-- Generated output files
CREATE TABLE generated_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,   -- Relative path in output directory
    file_type TEXT NOT NULL,          -- 'index', 'cluster', 'network', 'wikilink'
    source_data JSON,                 -- What data generated this file
    template_used TEXT,               -- Template file used
    generated_at TIMESTAMP NOT NULL,
    file_size INTEGER,
    checksum TEXT                     -- File content checksum
);

-- Wikilink mappings
CREATE TABLE wikilink_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_hash TEXT NOT NULL,
    target_hash TEXT NOT NULL,
    link_text TEXT NOT NULL,          -- Text displayed for link
    link_type TEXT NOT NULL,          -- 'similar', 'concept', 'reference'
    context TEXT,                     -- Context where link appears
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (source_hash) REFERENCES documents(content_hash),
    FOREIGN KEY (target_hash) REFERENCES documents(content_hash)
);

-- Output configurations
CREATE TABLE output_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_name TEXT NOT NULL UNIQUE,
    output_directory TEXT NOT NULL,
    template_settings JSON,
    generation_rules JSON,            -- Rules for what to generate
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    last_used TIMESTAMP
);

-- Generation history
CREATE TABLE generation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER NOT NULL,
    generation_type TEXT NOT NULL,    -- 'full', 'incremental', 'specific'
    files_generated INTEGER NOT NULL,
    files_updated INTEGER NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,             -- 'running', 'completed', 'failed'
    error_details TEXT,
    FOREIGN KEY (config_id) REFERENCES output_configs(id)
);
```

#### Key Services
- **WikilinkGenerationService**: Generate [[wikilinks]] between related documents
- **IndexGenerationService**: Create index and navigation files
- **VaultOrganizationService**: Organize output into logical vault structure
- **TemplateService**: Manage and apply output templates

#### API Endpoints
- `POST /obsidian/generate` - Generate Obsidian-compatible files
- `GET /obsidian/configs` - List output configurations
- `POST /obsidian/configs` - Create new output configuration
- `GET /obsidian/history` - Get generation history

#### Dependencies
- semantic_core (document data)
- cross_reference (relationships)
- clustering (themes and groupings)

---

### 8. modules/standard/incremental_processing/

**Purpose**: Change detection and selective updates

#### Files Structure
```
incremental_processing/
├── manifest.json
├── api.py
├── services.py
├── module_settings.py
├── monitors/
│   ├── file_monitor.py        # Watch for file changes
│   ├── content_monitor.py     # Detect content changes
│   └── dependency_monitor.py  # Track processing dependencies
├── processors/
│   ├── selective_processor.py # Process only changed documents
│   ├── dependency_processor.py # Process dependent documents
│   └── batch_optimizer.py     # Optimize processing batches
├── database.py
├── db_models.py
├── api_schemas.py
└── utils.py
```

#### Database Schema (incremental_processing.db)
```sql
-- File system monitoring
CREATE TABLE file_watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_path TEXT NOT NULL,         -- Directory or file being watched
    watch_type TEXT NOT NULL,         -- 'directory', 'file'
    last_scan TIMESTAMP NOT NULL,
    files_found INTEGER,
    changes_detected INTEGER,
    is_active BOOLEAN DEFAULT TRUE
);

-- Processing queue
CREATE TABLE processing_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL,
    change_type TEXT NOT NULL,        -- 'added', 'modified', 'deleted'
    priority INTEGER DEFAULT 100,     -- Processing priority
    dependencies JSON,                -- Other documents that depend on this
    queued_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'queued',     -- 'queued', 'processing', 'completed', 'failed'
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);

-- Processing dependencies
CREATE TABLE processing_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dependent_hash TEXT NOT NULL,     -- Document that depends on another
    dependency_hash TEXT NOT NULL,    -- Document being depended on
    dependency_type TEXT NOT NULL,    -- 'similarity', 'reference', 'cluster'
    last_processed TIMESTAMP,
    FOREIGN KEY (dependent_hash) REFERENCES documents(content_hash),
    FOREIGN KEY (dependency_hash) REFERENCES documents(content_hash),
    UNIQUE(dependent_hash, dependency_hash, dependency_type)
);

-- Update statistics
CREATE TABLE update_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,               -- Date of statistics
    files_scanned INTEGER NOT NULL,
    changes_detected INTEGER NOT NULL,
    documents_processed INTEGER NOT NULL,
    processing_time REAL,             -- Total processing time in seconds
    errors_encountered INTEGER DEFAULT 0
);
```

#### Key Services
- **ChangeDetectionService**: Monitor file system for changes
- **SelectiveProcessingService**: Process only changed documents
- **DependencyTrackingService**: Track and process dependent documents
- **UpdateOptimizationService**: Optimize incremental update strategies

#### API Endpoints
- `POST /incremental/scan` - Scan for changes
- `POST /incremental/process` - Process detected changes
- `GET /incremental/queue` - Get processing queue status
- `GET /incremental/stats` - Get update statistics

#### Dependencies
- semantic_core (document registry)
- document_processing (processing pipeline)
- vector_operations (embedding updates)

## Module Dependencies

### Dependency Graph
```
semantic_core (foundation)
    ↑
    ├── vector_operations
    ├── document_processing
    └── incremental_processing
        ↑
        ├── cross_reference (uses: semantic_core, vector_operations)
        ├── clustering (uses: semantic_core, vector_operations)
        └── cli_interface (uses: semantic_core, vector_operations, document_processing)
            ↑
            └── obsidian_integration (uses: semantic_core, cross_reference, clustering)
```

### Initialization Order
1. **semantic_core** - Foundation, no dependencies
2. **vector_operations** - Depends on document registry
3. **document_processing** - Depends on document registry
4. **incremental_processing** - Depends on semantic_core, document_processing
5. **cross_reference** - Depends on semantic_core, vector_operations
6. **clustering** - Depends on semantic_core, vector_operations
7. **cli_interface** - Depends on multiple modules for commands
8. **obsidian_integration** - Depends on analysis results from other modules

## Configuration Management

### Framework Settings (data/settings.json)
```json
{
  "standard.semantic_core": {
    "source_directory": "/path/to/vef/documents",
    "supported_extensions": [".md", ".markdown"],
    "content_hash_algorithm": "sha256",
    "auto_scan_enabled": true,
    "scan_interval_seconds": 300
  },
  "standard.vector_operations": {
    "model_name": "mixedbread-ai/mxbai-embed-large-v1",
    "embedding_dimensions": 1024,
    "similarity_threshold_default": 0.7,
    "batch_size": 32,
    "chromadb_persist_directory": "data/chromadb"
  },
  "standard.document_processing": {
    "max_concurrent_jobs": 4,
    "processing_timeout_seconds": 300,
    "retry_attempts": 3,
    "content_preview_length": 200
  },
  "standard.cli_interface": {
    "default_output_format": "json",
    "cache_enabled": true,
    "cache_ttl_seconds": 3600,
    "session_timeout_minutes": 60
  },
  "standard.clustering": {
    "default_algorithm": "adaptive",
    "min_cluster_size": 3,
    "max_clusters": 20,
    "quality_threshold": 0.6
  },
  "standard.obsidian_integration": {
    "default_output_directory": "outputs/obsidian",
    "generate_index_files": true,
    "wikilink_style": "[[filename]]",
    "include_metadata": true
  },
  "standard.incremental_processing": {
    "scan_interval_seconds": 60,
    "batch_processing_size": 10,
    "dependency_tracking_enabled": true,
    "auto_process_changes": true
  }
}
```

### Environment Variables (.env)
```bash
# Model access (if needed)
HUGGINGFACE_TOKEN=your_token_here

# External APIs (future)
OPENAI_API_KEY=your_key_here

# Development settings
DEBUG=false
LOG_LEVEL=info
```

## Development Tools Integration

### Scaffolding Command
```bash
# Create new semantic analyzer module
python tools/scaffold_module.py semantic_analyzer_module \
    --template standard \
    --features database,api,settings \
    --dependencies semantic_core,vector_operations
```

### Compliance Checking
```bash
# Validate all semantic analyzer modules
python tools/compliance/compliance.py --validate-group semantic_analyzer

# Validate specific module
python tools/compliance/compliance.py --validate standard.semantic_core
```

### Database Inspection
```bash
# Inspect semantic_core database
python tools/database_inspection/inspect_sqlite.py semantic_core

# Inspect ChromaDB collections
python tools/database_inspection/inspect_chromadb.py vector_operations
```

## Testing Strategy

### Unit Testing
- Each module has comprehensive unit tests in `tests/modules/standard/module_name/`
- Use framework's testing utilities for database and service testing
- Mock dependencies using standardized patterns

### Integration Testing
- Test module interactions through API endpoints
- Validate data flow between modules
- Test complete workflows (document ingestion → analysis → output)

### Performance Testing
- Benchmark similarity search performance with 500+ documents
- Test memory usage during bulk processing
- Validate sub-2s response time requirements

## Migration Plan Summary

### Phase 1: Core Infrastructure
1. Set up modular framework with semantic analyzer project structure
2. Implement semantic_core module with document registry
3. Implement vector_operations module with ChromaDB integration
4. Migrate existing VEF documents to new structure

### Phase 2: Processing Pipeline
1. Implement document_processing module
2. Implement cli_interface module with basic commands
3. Port existing analyze.py functionality
4. Validate all CLI commands work correctly

### Phase 3: Advanced Features
1. Implement cross_reference module
2. Implement clustering module  
3. Implement obsidian_integration module
4. Add incremental_processing module

### Phase 4: Production Readiness
1. Complete testing and optimization
2. Add comprehensive error handling
3. Create deployment documentation
4. Performance tuning and monitoring

This modular structure provides a clean, maintainable foundation that eliminates the current technical debt while preserving all functional requirements. The framework's standardized patterns ensure consistent development and easy future maintenance.