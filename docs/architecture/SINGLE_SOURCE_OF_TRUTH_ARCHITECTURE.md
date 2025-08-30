# SINGLE SOURCE OF TRUTH ARCHITECTURE

## CRITICAL: Database Responsibility Boundaries

This document establishes the authoritative data ownership rules to prevent data duplication and maintain architectural integrity.

---

## Source of Truth Designation

### semantic_core.db = THE ONLY SOURCE OF TRUTH
**Authoritative for ALL document information:**
- Document registry (what documents exist in the system)
- Document metadata (content_hash, file_path, filename, size, etc.)
- Document content (content_preview, word_count, etc.)
- Document lifecycle (when added, modified, last_processed, etc.)
- Document relationships and categorization

**ALL other modules must reference semantic_core.db for document information**

### vector_operations.db = ChromaDB Management ONLY
**Strictly limited to embedding operations:**
- ChromaDB collection tracking (collection_name, model, dimension)
- Embedding status tracking (which content_hashes have embeddings)
- ChromaDB-specific identifiers (chroma_document_id, collection_id)
- Query history and performance metrics
- Similarity search results and caching

**FORBIDDEN in vector_operations.db:**
- Document file paths
- Document filenames  
- Document content
- Document sizes
- Document modification times
- ANY document metadata that exists in semantic_core.db

---

## Data Flow Architecture

### Correct Pattern: Reference by content_hash
```python
# vector_operations queries semantic_core for document info
document_info = await semantic_core_service.get_document_by_hash(content_hash)
file_path = document_info.data["file_path"]
filename = document_info.data["filename"]

# vector_operations only stores embedding status
await vector_db.store({
    "content_hash": content_hash,  # Link to semantic_core
    "chroma_document_id": chroma_id,
    "embedding_model": model_name,
    # NO file_path, filename, or other document metadata
})
```

### FORBIDDEN Pattern: Duplicate document data
```python
# NEVER DO THIS - Creates dual source of truth
await vector_db.store({
    "content_hash": content_hash,
    "file_path": file_path,        # ❌ FORBIDDEN - belongs in semantic_core
    "filename": filename,          # ❌ FORBIDDEN - belongs in semantic_core
    "file_size": size,            # ❌ FORBIDDEN - belongs in semantic_core
    "chroma_document_id": chroma_id
})
```

---

## Module Responsibilities

### semantic_core
**"Document Registry Authority"**
- Register new documents
- Store all document metadata
- Provide document lookup by content_hash
- Track document changes and lifecycle
- Serve as API for document information to other modules

### vector_operations  
**"Embedding Service"**
- Create embeddings for documents (by content_hash)
- Track embedding status in ChromaDB
- Manage similarity queries
- Store ONLY embedding-related operational data
- Query semantic_core when document info is needed

### document_processing
**"Content Extraction Service"**
- Extract content from external files
- Pass structured data to semantic_core for registration
- NO persistent storage of document metadata

---

## Implementation Rules

### 1. Cross-Module Data Access
```python
# CORRECT: vector_operations gets document info from semantic_core
semantic_core_service = app_context.get_service("semantic_core.service")
doc_result = await semantic_core_service.get_document_by_hash(content_hash)
if doc_result.success:
    file_path = doc_result.data["file_path"]
    # Use file_path for processing

# FORBIDDEN: vector_operations stores its own copy of file_path
```

### 2. Database Schema Rules
**vector_operations tables MUST only contain:**
- content_hash (as foreign key reference)
- ChromaDB-specific identifiers
- Embedding model and dimension info
- Query and performance metrics
- Timestamps related to embedding operations

**vector_operations tables MUST NOT contain:**
- file_path, filename, file_size
- document content or previews  
- word counts or document statistics
- document modification times
- ANY data that exists in semantic_core.db

### 3. API Design Rules
```python
# CORRECT: Return content_hash, let caller get document info
return {
    "embeddings": [
        {"content_hash": "abc123...", "similarity": 0.95},
        {"content_hash": "def456...", "similarity": 0.87}
    ]
}

# FORBIDDEN: Duplicate document information in response
return {
    "embeddings": [
        {
            "content_hash": "abc123...", 
            "similarity": 0.95,
            "file_path": "/path/to/file.md",  # ❌ Should come from semantic_core
            "filename": "file.md"             # ❌ Should come from semantic_core
        }
    ]
}
```

---

## Verification Checklist

### Before Adding Any Field to vector_operations.db:
- [ ] Does this field exist in semantic_core.db?
- [ ] Is this field specific to embedding operations?
- [ ] Would losing this field break ChromaDB management?
- [ ] Can this information be retrieved from semantic_core when needed?

**If ANY of the first two questions is "yes", the field belongs in semantic_core.db, not vector_operations.db**

### Code Review Requirements:
- [ ] No document metadata duplication across databases
- [ ] All document info queries go through semantic_core service
- [ ] vector_operations only stores embedding operational data
- [ ] content_hash used as sole link between modules

---

## Benefits of This Architecture

### 1. Data Integrity
- Single authoritative source for document information
- No synchronization issues between databases
- Clear ownership of data types

### 2. Maintainability  
- Document schema changes only affect semantic_core
- vector_operations remains stable as embedding service
- Clear module boundaries and responsibilities

### 3. Scalability
- Each database optimized for its specific use case
- No unnecessary data duplication
- Clean service interfaces

---

## VIOLATION CONSEQUENCES

**ANY violation of these rules creates architectural debt and data integrity issues:**

1. **Data Inconsistency**: Multiple sources of truth lead to conflicting information
2. **Maintenance Burden**: Schema changes require updates in multiple places
3. **Bug Introduction**: Synchronization failures between duplicated data
4. **Architecture Corruption**: Blurred module responsibilities

**If document metadata is found in vector_operations.db:**
1. **Immediate removal** - Delete the duplicated fields
2. **Replace with queries** - Use semantic_core service for document info
3. **Update APIs** - Return content_hash only, let callers get document details
4. **Verify integrity** - Ensure no other modules store document metadata

---

## SUMMARY

- **semantic_core.db**: THE source of truth for all document information
- **vector_operations.db**: ChromaDB management and embedding operations only
- **All document metadata queries**: Go through semantic_core service
- **Cross-module references**: Use content_hash only
- **Zero tolerance**: For document metadata duplication

This architecture ensures clean separation of concerns and prevents the dual source of truth anti-pattern that leads to data inconsistency and maintenance issues.