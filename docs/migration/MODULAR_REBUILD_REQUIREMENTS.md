# Modular Framework Rebuild Requirements

## Project Overview

Rebuild the Semantic Document Analyzer using the proven modular framework architecture to eliminate technical debt and create a maintainable, extensible system for VEF Framework document analysis.

## Core Requirements

### Functional Requirements

#### 1. Document Analysis
- **VEF Document Processing**: Parse and analyze VEF Framework markdown documents
- **Semantic Embeddings**: Generate embeddings using existing mixedbread-ai/mxbai-embed-large-v1 model
- **Content Hashing**: SHA256-based document identification for change detection
- **Metadata Extraction**: Word count, categories, relative paths, modification times

#### 2. Similarity Search  
- **Document-to-Document**: Find documents similar to a reference document
- **Concept Search**: Find documents by semantic concept or search term
- **Configurable Thresholds**: Similarity thresholds and result limits
- **Ranked Results**: Sorted by similarity score with metadata enrichment

#### 3. Document Organization
- **Cross-Reference Analysis**: Identify shared concepts and relationships
- **Clustering**: Group documents by semantic themes and categories
- **Theme Detection**: Automatic categorization of VEF concepts
- **Obsidian Integration**: Generate wikilinks and index files

#### 4. Command-Line Interface
- **analyze.py**: Maintain existing CLI command structure  
- **Real-time Response**: Sub-500ms response times for status/worker commands
- **Progressive Detail**: Document → paragraph → sentence → concept analysis levels
- **Output Formats**: JSON, table, file output with configurable verbosity

### Non-Functional Requirements

#### 1. Data Integrity (Critical)
- **Absolute Truth Correspondence**: No mock data, placeholders, or simulated results
- **Hard Failure Pattern**: Unimplemented features must fail clearly with TODO comments
- **Content-Hash Consistency**: Single source of truth for document identification
- **Audit Trail**: Complete tracking of document processing and analysis

#### 2. Performance
- **Sub-500ms CLI**: Status and worker commands must respond quickly
- **Efficient Similarity**: Sub-2s similarity search for 500 document collection  
- **Memory Management**: Handle 5.4MB document collection efficiently
- **Incremental Processing**: Only reprocess changed documents

#### 3. Maintainability
- **Module Isolation**: Each module independently testable and debuggable
- **Clear Dependencies**: Explicit module dependencies via manifest.json
- **Standardized Patterns**: Follow modular framework conventions
- **Comprehensive Logging**: Debug-friendly logging throughout

#### 4. Extensibility
- **New Analysis Types**: Easy addition of analysis algorithms
- **Output Formats**: Pluggable output generation (Obsidian, reports, APIs)
- **Data Sources**: Support for additional document types beyond markdown
- **Integration Points**: API endpoints for external tool integration

## Technical Requirements

### Architecture

#### 1. Modular Framework Compliance
- **Framework Version**: Use latest python_modular_framework patterns
- **Two-Phase Initialization**: Service registration → complex setup
- **Result Pattern**: All operations return standardized Result objects
- **Database Per Module**: Each module manages its own SQLite database
- **Settings Management**: Framework-integrated configuration system

#### 2. Database Architecture
- **Table-Driven Patterns**: Use framework's get_database_base() approach
- **Content-Hash Primary Keys**: SHA256 hashes as document identifiers
- **Relational Integrity**: Proper foreign keys and constraints
- **Migration Support**: Framework-integrated database migrations
- **No Legacy Support**: Clean slate, no backward compatibility needed

#### 3. API Design
- **FastAPI Integration**: Framework-integrated API endpoints
- **Async Throughout**: Fully asynchronous operation
- **Error Handling**: Standardized error responses and logging
- **Documentation**: Auto-generated OpenAPI documentation

### Module Structure

#### Core Modules (Required)

##### 1. semantic_core
- **Purpose**: Document metadata and content storage
- **Database**: documents table with content hashes, paths, metadata
- **Dependencies**: None (core module)
- **Key Functions**: Document registration, content hashing, metadata storage

##### 2. vector_operations  
- **Purpose**: ChromaDB embeddings and similarity operations
- **Database**: ChromaDB instance for embeddings storage
- **Dependencies**: semantic_core
- **Key Functions**: Embedding generation, similarity search, vector operations

##### 3. document_processing
- **Purpose**: File parsing and content extraction  
- **Database**: processing_status, extraction_metadata
- **Dependencies**: semantic_core
- **Key Functions**: Markdown parsing, content extraction, format handling

##### 4. cli_interface
- **Purpose**: analyze.py command implementations
- **Database**: command_history, session_tracking
- **Dependencies**: semantic_core, vector_operations, document_processing
- **Key Functions**: CLI command routing, output formatting, session management

#### Feature Modules (Secondary)

##### 5. cross_reference_analysis
- **Purpose**: Document relationship analysis
- **Database**: relationships, shared_concepts, reference_networks
- **Dependencies**: semantic_core, vector_operations
- **Key Functions**: Relationship detection, concept mapping, network analysis

##### 6. document_clustering
- **Purpose**: Document grouping and theme detection
- **Database**: clusters, cluster_assignments, cluster_analysis
- **Dependencies**: vector_operations
- **Key Functions**: K-means clustering, theme detection, category assignment

##### 7. obsidian_integration
- **Purpose**: Obsidian-compatible output generation
- **Database**: output_templates, generated_files, link_mapping
- **Dependencies**: semantic_core, cross_reference_analysis
- **Key Functions**: Wikilink generation, index creation, vault organization

##### 8. incremental_processing
- **Purpose**: Change detection and selective updates
- **Database**: change_log, processing_queue, update_status
- **Dependencies**: semantic_core, document_processing
- **Key Functions**: File monitoring, change detection, selective reprocessing

### Data Requirements

#### 1. Input Data
- **Source Directory**: VEF Framework Obsidian vault (480 markdown files, ~5.4MB)
- **File Formats**: Markdown (.md) files with front matter
- **Content Types**: Philosophical framework documents, analysis, methodology
- **Encoding**: UTF-8 text with standard markdown formatting

#### 2. Storage Requirements
- **Total Storage**: <100MB for processed data (embeddings + metadata)
- **Database Files**: Multiple SQLite files per module design
- **ChromaDB Storage**: Efficient vector storage for 480 document embeddings
- **Configuration**: JSON-based settings with framework integration

#### 3. Output Requirements
- **CLI Outputs**: JSON, tabular, file formats with configurable verbosity
- **Obsidian Files**: Wikilink-compatible markdown with index files
- **API Responses**: JSON with comprehensive metadata and pagination
- **Reports**: Analysis summaries and statistics in multiple formats

### Performance Requirements

#### 1. Response Times
- **Status Commands**: <100ms (cached system status)
- **Worker Commands**: <200ms (worker pool management)
- **Similarity Search**: <2s for 10 results from 480 documents
- **Document Processing**: <30s for full collection reprocessing
- **Incremental Updates**: <5s for single document updates

#### 2. Resource Usage  
- **Memory**: <2GB peak usage during full processing
- **Storage**: <100MB total for processed data
- **CPU**: Efficient use of available cores for embedding generation
- **Database**: Sub-100ms query response times for metadata operations

#### 3. Scalability
- **Document Count**: Support up to 1000 documents efficiently
- **Concurrent Users**: Handle multiple CLI sessions simultaneously  
- **API Load**: Support moderate API usage for external integrations
- **Background Processing**: Non-blocking incremental updates

### Quality Requirements

#### 1. Reliability
- **Data Consistency**: Atomic operations for database updates
- **Error Recovery**: Graceful handling of processing failures
- **Validation**: Input validation throughout processing pipeline
- **Backup/Recovery**: Framework-integrated backup mechanisms

#### 2. Security
- **Input Sanitization**: Safe handling of markdown content
- **Path Traversal Prevention**: Secure file path handling
- **API Security**: Rate limiting and input validation for API endpoints
- **Configuration Security**: Secure storage of sensitive settings

#### 3. Usability
- **Clear Error Messages**: Human-readable error descriptions with context
- **Progress Feedback**: Real-time progress for long-running operations  
- **Debug Mode**: Verbose logging for troubleshooting
- **Documentation**: Comprehensive API and CLI documentation

## Migration Strategy

### Phase 1: Core Infrastructure (Week 1)
1. **Framework Setup**: Initialize modular framework with semantic analyzer project
2. **Core Modules**: Implement semantic_core and vector_operations modules
3. **Basic CLI**: Port essential analyze.py commands (status, basic similarity)
4. **Data Migration**: Import existing VEF documents into new module structure

### Phase 2: Feature Parity (Week 2)  
1. **Advanced CLI**: Implement remaining analyze.py commands
2. **Processing Pipeline**: Complete document_processing module
3. **Cross-References**: Port cross-reference analysis functionality
4. **Testing**: Comprehensive testing of core functionality

### Phase 3: Enhanced Features (Week 3)
1. **Clustering**: Implement document clustering and theme detection
2. **Obsidian Integration**: Generate wikilinks and index files
3. **Incremental Processing**: Change detection and selective updates
4. **API Refinement**: Polish API endpoints and documentation

### Phase 4: Production Readiness (Week 4)
1. **Performance Optimization**: Query optimization and caching
2. **Error Handling**: Comprehensive error handling and recovery
3. **Documentation**: Complete user and developer documentation  
4. **Deployment**: Production-ready configuration and deployment scripts

## Success Criteria

### Immediate Success (End of Phase 2)
- [ ] All existing analyze.py commands work correctly
- [ ] Similarity search returns accurate results consistently
- [ ] No technical debt or scattered implementations  
- [ ] All modules pass framework compliance checks
- [ ] Sub-2s similarity search performance achieved

### Long-term Success (End of Phase 4)
- [ ] System handles 1000+ documents efficiently
- [ ] External API integrations work seamlessly
- [ ] Incremental processing reduces full reprocessing needs
- [ ] Comprehensive documentation enables easy maintenance
- [ ] Framework patterns enable rapid feature development

## Risk Mitigation

### Technical Risks
- **Framework Learning Curve**: Mitigated by comprehensive framework documentation
- **Performance Regression**: Mitigated by performance benchmarks and monitoring
- **Data Migration Issues**: Mitigated by incremental migration with validation
- **Integration Complexity**: Mitigated by modular design and clear interfaces

### Project Risks  
- **Scope Creep**: Mitigated by clear phase boundaries and success criteria
- **Timeline Pressure**: Mitigated by working core functionality first
- **Quality Compromise**: Mitigated by framework compliance requirements
- **User Disruption**: Mitigated by maintaining CLI interface compatibility

## Conclusion

This rebuild represents a strategic investment in technical architecture that will:
- Eliminate current technical debt completely
- Provide a maintainable foundation for future development
- Enable rapid feature development using proven patterns
- Ensure VEF Framework data integrity requirements are met
- Create a professional-grade tool worthy of the VEF methodology

The modular framework provides the proven patterns and tools needed to execute this rebuild successfully while preventing the accumulation of new technical debt.