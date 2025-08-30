# Semantic Document Analyzer API Reference

This document provides a comprehensive reference for all API endpoints available in the Semantic Document Analyzer v2 framework.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently no authentication required for local development.

---

## Semantic CLI Module

### Analyze Documents
**Primary command for document analysis pipeline**

```http
POST /api/v1/semantic_cli/analyze
```

**Request Body:**
```json
{
  "source_dir": "path/to/documents",
  "force_reprocess": false,
  "detail_level": "document"
}
```

**Parameters:**
- `source_dir` (string, required): Directory containing markdown documents to analyze
- `force_reprocess` (boolean, optional, default=false): Force reprocessing of existing embeddings
- `detail_level` (string, optional, default="document"): Level of analysis detail

**Response:**
```json
{
  "success": true,
  "data": {
    "analysis_type": "full_analysis",
    "source_directory": "test_documents",
    "detail_level": "document",
    "force_reprocess": false,
    "processing_summary": {
      "total_files": 3,
      "processed_documents": 3,
      "processing_errors": 0
    },
    "registration_summary": {
      "registered_documents": 3,
      "registration_errors": 0
    },
    "embedding_summary": {
      "embedded_documents": 3,
      "embedding_errors": 0
    },
    "errors": {
      "processing_errors": [],
      "registration_errors": [],
      "embedding_errors": []
    },
    "completed_at": "2025-07-17T21:52:03.687739"
  },
  "processing_time": "N/A"
}
```

### System Status
**Get comprehensive system status across all modules**

```http
GET /api/v1/semantic_cli/system-status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "timestamp": "2025-07-17T21:44:43.815690",
    "overall_status": "healthy|degraded|error",
    "modules": {
      "semantic_core": { /* module status */ },
      "vector_operations": {
        "collection_name": "documents",
        "embedding_model": "mixedbread-ai/mxbai-embed-large-v1",
        "dimension": 1024,
        "document_count": 3,
        "total_chunks": 10
      },
      "document_processing": { /* module status */ }
    },
    "summary": {
      "total_documents": 0,
      "total_embeddings": 0,
      "pending_changes": 0
    }
  }
}
```

### Service Status
**Get semantic_cli module status**

```http
GET /api/v1/semantic_cli/status
```

### Service Info
**Get semantic_cli module information**

```http
GET /api/v1/semantic_cli/info
```

---

## Vector Operations Module

### Create Collection
**Create a new ChromaDB collection for vector storage**

```http
POST /api/v1/vector_operations/collections
```

**Request Body:**
```json
{
  "name": "documents",
  "description": "Document collection for semantic analysis",
  "embedding_model": "mixedbread-ai/mxbai-embed-large-v1"
}
```

### Add Document Embeddings
**Add document embeddings to a collection**

```http
POST /api/v1/vector_operations/embeddings
```

**Request Body:**
```json
{
  "content_hash": "sha256_hash_here",
  "content": "Document content to embed",
  "collection_name": "documents",
  "force_reprocess": false
}
```

### Search Similar Documents
**Perform similarity search using vector embeddings**

```http
POST /api/v1/vector_operations/search
```

**Request Body:**
```json
{
  "query_text": "Text to search for",
  "collection_name": "documents",
  "n_results": 10,
  "distance_threshold": 0.7
}
```

### Get Collection Status
**Get status and statistics for a ChromaDB collection**

```http
GET /api/v1/vector_operations/collections/{collection_name}/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "collection_name": "documents",
    "embedding_model": "mixedbread-ai/mxbai-embed-large-v1",
    "dimension": 1024,
    "distance_metric": "cosine",
    "document_count": 3,
    "total_chunks": 10,
    "embedding_records": 10,
    "chroma_document_count": 10,
    "is_active": true
  }
}
```

### Service Status
```http
GET /api/v1/vector_operations/status
```

### Service Info
```http
GET /api/v1/vector_operations/info
```

---

## Semantic Core Module

### Register Document
**Register a single document in the semantic core**

```http
POST /api/v1/semantic_core/documents/register
```

### Bulk Register Documents
**Register multiple documents at once**

```http
POST /api/v1/semantic_core/documents
```

### Get Document by Hash
**Retrieve document information by content hash**

```http
GET /api/v1/semantic_core/documents/{content_hash}
```

### Get Documents List
**Get list of all registered documents**

```http
GET /api/v1/semantic_core/documents
```

### Registry Status
**Get document registry statistics**

```http
GET /api/v1/semantic_core/status/registry
```

### Service Status
```http
GET /api/v1/semantic_core/status
```

### Service Info
```http
GET /api/v1/semantic_core/info
```

---

## Document Processing Module

### Process Single File
**Process a single markdown file**

```http
POST /api/v1/document_processing/process
```

**Request Body:**
```json
{
  "file_path": "path/to/document.md",
  "extract_metadata": true,
  "clean_content": true
}
```

### Extract Text Content
**Extract text content from a document**

```http
POST /api/v1/document_processing/extract-text
```

### Get Processing Summary
**Get summary of document processing operations**

```http
GET /api/v1/document_processing/summary
```

### Service Status
```http
GET /api/v1/document_processing/status
```

### Service Info
```http
GET /api/v1/document_processing/info
```

---

## Core Framework Endpoints

### Database Status
**Check database health and connectivity**

```http
GET /api/v1/db/status
```

### Database Tables
**List all database tables**

```http
GET /api/v1/db/tables
```

### Table Schema
**Get schema for a specific table**

```http
GET /api/v1/db/tables/{table_name}/schema
```

### Settings Management
**Get/update module settings**

```http
GET /api/v1/settings/
POST /api/v1/settings/
GET /api/v1/settings/{module_id}/{setting_name}
```

### System Health
**Overall system health check**

```http
GET /api/v1/system/health
```

### Module Registry
**Get information about all loaded modules**

```http
GET /api/v1/modules/registry
```

### Session Information
**Get current application session info**

```http
GET /api/v1/global/session-info
```

---

## Common Response Patterns

### Success Response
```json
{
  "success": true,
  "data": { /* response data */ },
  "processing_time": "1.23s"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": { /* additional error context */ }
  }
}
```

---

## CLI Development Notes

### Key Endpoints for CLI Tools

**Primary Analysis Command:**
- `POST /api/v1/semantic_cli/analyze` - Main document analysis pipeline

**Status Checking:**
- `GET /api/v1/semantic_cli/system-status` - Comprehensive system overview
- `GET /api/v1/vector_operations/collections/documents/status` - Vector operations status
- `GET /api/v1/semantic_core/status/registry` - Document registry status

**Manual Operations:**
- `POST /api/v1/vector_operations/search` - Similarity search
- `GET /api/v1/semantic_core/documents` - List documents
- `GET /api/v1/document_processing/summary` - Processing statistics

### Configuration Settings

**Vector Operations Configuration:**
- Embedding Model: `mixedbread-ai/mxbai-embed-large-v1`
- Device: `cuda` (GPU acceleration)
- Dimensions: `1024`
- Chunk Size: `1000` characters
- Chunk Overlap: `100` characters

**Force Reprocessing:**
- Always use `force_reprocess=false` by default
- Only use `force_reprocess=true` when explicitly requested by user
- Force reprocessing cleanly removes existing embeddings before recreating

---

## Framework Architecture Notes

### Database Pattern
- All modules use framework's centralized database service
- No direct model imports in service methods after initialization
- Raw SQL queries for all database operations
- Content hash (SHA256) is the universal document identifier

### Error Handling
- All endpoints use Result pattern for consistent error handling
- Comprehensive logging for debugging
- Graceful degradation when modules are unavailable

### Module Dependencies
- `semantic_cli` orchestrates `semantic_core`, `vector_operations`, and `document_processing`
- `vector_operations` depends on ChromaDB for vector storage
- `semantic_core` manages document registry and metadata
- `document_processing` handles file parsing and content extraction

---

*Last Updated: 2025-07-17*
*Framework Version: 0.1.0*
*Semantic Analyzer Version: 2.0*