# Database Inspection Guide for Semantic Document Analyzer

This guide covers using the database inspection tools specifically for the Semantic Document Analyzer v2.

## Overview

The framework includes standalone database inspection tools that work **without requiring the application to be running**. These are invaluable for debugging, validation, and development.

## Available Tools

### 1. ChromaDB Inspection Tool
**Location**: `tools/database_inspection/inspect_chromadb.py`
**Target**: Vector embeddings storage (`data/chroma_db/`)

### 2. SQLite Inspection Tool  
**Location**: `tools/database_inspection/inspect_sqlite.py`
**Target**: Metadata databases (`data/database/*.db`)

---

## Semantic Analyzer Database Architecture

### ChromaDB Structure
**Location**: `data/chroma_db/`
- **Collection**: `documents` - Main document embeddings
- **Model**: `mixedbread-ai/mxbai-embed-large-v1`
- **Dimensions**: 1024
- **Storage**: Vector embeddings + metadata

### SQLite Databases
**Location**: `data/database/`

#### vector_operations.db
- `vector_collections` - ChromaDB collection metadata
- `document_embeddings` - Embedding records with content hashes
- `similarity_queries` - Search query history
- `similarity_results` - Search result details

#### semantic_core.db  
- `documents` - Document registry
- `document_changes` - Change tracking
- `content_cache` - Processed content cache

#### framework.db
- Core framework data (settings, logs, scheduler)

---

## Common Inspection Tasks

### 1. Verify System Health
```bash
# Check ChromaDB collection status
python tools/database_inspection/inspect_chromadb.py --dir data/chroma_db --stats

# Expected output:
# 📦 documents: 10 documents
# Description: Default document collection

# Check vector operations database
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --list

# Expected output:
# 📊 document_embeddings (table): 10 rows
# 📊 vector_collections (table): 1 rows
```

### 2. Validate GPU Model Upgrade
```bash
# Verify mixedbread model is being used
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --query "SELECT DISTINCT embedding_model, vector_dimension FROM document_embeddings"

# Expected output:
# embedding_model: mixedbread-ai/mxbai-embed-large-v1
# vector_dimension: 1024
```

### 3. Check Force Reprocessing Results
```bash
# Verify no duplicate embeddings exist
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --query "SELECT content_hash, COUNT(*) FROM document_embeddings GROUP BY content_hash HAVING COUNT(*) > 3"

# Should return no results if force reprocessing worked correctly
```

### 4. Database Consistency Verification
```bash
# Check ChromaDB vs SQLite alignment
echo "ChromaDB:" && python tools/database_inspection/inspect_chromadb.py --dir data/chroma_db --stats | grep "documents:"
echo "SQLite:" && python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --query "SELECT COUNT(*) as embedding_count FROM document_embeddings"

# Counts should match (e.g., 10 documents in both)
```

---

## Advanced Debugging

### Content Hash Analysis
```bash
# View document content hashes and chunk distribution
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --query "
SELECT 
  content_hash, 
  COUNT(*) as chunks, 
  AVG(chunk_size) as avg_size,
  MAX(chunk_index) + 1 as total_chunks
FROM document_embeddings 
GROUP BY content_hash"
```

### Processing Performance Analysis
```bash
# Check embedding generation performance
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --query "
SELECT 
  DATE(processed_at) as date,
  COUNT(*) as chunks_processed,
  AVG(processing_duration_ms) as avg_duration,
  MIN(processing_duration_ms) as min_duration,
  MAX(processing_duration_ms) as max_duration
FROM document_embeddings 
GROUP BY DATE(processed_at)"
```

### Collection Metadata Inspection
```bash
# View detailed collection information
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --table vector_collections --limit 1

# Expected key fields:
# - embedding_model: mixedbread-ai/mxbai-embed-large-v1
# - dimension: 1024
# - document_count: 3
# - total_chunks: 10
```

---

## Interactive Mode Features

### ChromaDB Interactive Mode
```bash
python tools/database_inspection/inspect_chromadb.py --dir data/chroma_db --interactive
```

Features:
- **Collection Browser**: Navigate between collections
- **Document Explorer**: Browse embeddings with pagination
- **Search Interface**: Test similarity searches
- **Export Function**: Save data to JSON files

### SQLite Interactive Mode
```bash
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --interactive
```

Features:
- **Table Browser**: Navigate database tables
- **Data Browser**: Browse records with pagination
- **Query Console**: Execute custom SQL queries
- **Schema Viewer**: View table structures and indexes

---

## Troubleshooting Common Issues

### No Documents in ChromaDB
```bash
# Check if analyze command was run
python tools/database_inspection/inspect_chromadb.py --dir data/chroma_db --stats

# If 0 documents, run analyze:
curl -X POST "http://localhost:8000/api/v1/semantic_cli/analyze" \
  -H "Content-Type: application/json" \
  -d '{"source_dir": "test_documents"}'
```

### Model Inconsistency
```bash
# Check for mixed embedding models (should all be mixedbread)
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --query "SELECT embedding_model, COUNT(*) FROM document_embeddings GROUP BY embedding_model"

# If mixed models found, force reprocess:
curl -X POST "http://localhost:8000/api/v1/semantic_cli/analyze" \
  -H "Content-Type: application/json" \
  -d '{"source_dir": "test_documents", "force_reprocess": true}'
```

### Database Lock Issues
```bash
# Check for database locks (WAL files)
ls -la data/database/*.db-wal

# If WAL files exist, ensure app is stopped before inspection
```

---

## Export and Backup

### Export Collection Data
```bash
# Export ChromaDB collection to JSON
python tools/database_inspection/inspect_chromadb.py --dir data/chroma_db --collection documents --json > embeddings_backup.json

# Export SQLite table to JSON
python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --table document_embeddings --json > embeddings_metadata.json
```

### Database Schema Documentation
```bash
# Generate schema documentation for all tables
for table in vector_collections document_embeddings similarity_queries similarity_results; do
  echo "## Table: $table" >> schema_docs.md
  python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --table $table --schema >> schema_docs.md
  echo "" >> schema_docs.md
done
```

---

## Development Workflow Integration

### Pre-Commit Validation
```bash
#!/bin/bash
# Add to pre-commit hook

echo "Validating database consistency..."

# Check ChromaDB collection exists
CHROMA_COUNT=$(python tools/database_inspection/inspect_chromadb.py --dir data/chroma_db --stats 2>/dev/null | grep "documents:" | grep -o '[0-9]*' || echo "0")

# Check SQLite embeddings exist  
SQLITE_COUNT=$(python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --query "SELECT COUNT(*) FROM document_embeddings" 2>/dev/null | grep -o '[0-9]*' || echo "0")

if [ "$CHROMA_COUNT" != "$SQLITE_COUNT" ]; then
  echo "❌ Database inconsistency: ChromaDB=$CHROMA_COUNT, SQLite=$SQLITE_COUNT"
  exit 1
fi

echo "✅ Database consistency verified: $CHROMA_COUNT documents"
```

### Post-Analysis Verification
```bash
# After running analyze command, verify results
function verify_analysis() {
  echo "Verifying analysis results..."
  
  # Check model consistency
  MODEL_CHECK=$(python tools/database_inspection/inspect_sqlite.py --db-path data/database/vector_operations.db --query "SELECT DISTINCT embedding_model FROM document_embeddings" | grep mixedbread)
  
  if [[ -z "$MODEL_CHECK" ]]; then
    echo "❌ Mixedbread model not found in embeddings"
    return 1
  fi
  
  echo "✅ Analysis verification complete"
}
```

---

## Key Advantages

### Standalone Operation
- **No framework dependency** - works when app is down
- **Direct database access** - no API layer
- **Faster inspection** - no service overhead

### Comprehensive Coverage
- **Vector data** (ChromaDB) and **metadata** (SQLite)
- **Schema inspection** and **data browsing**
- **Search and filtering** capabilities

### Development-Friendly
- **Interactive modes** for exploration
- **JSON export** for scripting
- **Custom queries** for specific analysis

---

*These tools are essential for maintaining and debugging the semantic analyzer's database architecture. Use them regularly during development and troubleshooting.*

---

*Last Updated: 2025-07-17*
*Compatible with: Semantic Analyzer v2, Framework v0.1.0*