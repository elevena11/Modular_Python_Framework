# Progressive Detail Architecture - Multi-Level Analysis System

**Date**: 2025-07-15  
**Purpose**: Define the progressive detail level system for semantic document analysis

## Vision: Detail Level "Slider"

The analysis system supports 4 progressive detail levels, each building on the previous:

### Level 1: Document (Current Implementation)
- **Granularity**: One embedding per document
- **Purpose**: General sorting and document-level clustering
- **Use Case**: High-level document organization
- **Status**: Ready to implement (fix ChromaDB metadata)

### Level 2: Paragraph (Planned)
- **Granularity**: One embedding per paragraph
- **Purpose**: Detailed content analysis and cross-referencing
- **Use Case**: Finding specific content within documents
- **Status**: Future implementation

### Level 3: Sentence (Planned)
- **Granularity**: One embedding per sentence
- **Purpose**: Precise content matching and fine-grained analysis
- **Use Case**: Detailed semantic search and citation
- **Status**: Future implementation

### Level 4: Concept (Planned - LLM Enhanced)
- **Granularity**: LLM-analyzed concepts per paragraph
- **Purpose**: VEF Framework concept mapping and categorization
- **Use Case**: Philosophical concept navigation and framework alignment
- **Status**: Future implementation

## Technical Architecture

### Progressive Enhancement Design
```python
class AnalysisDetailLevel(Enum):
    DOCUMENT = "document"      # Level 1: Document-level embeddings
    PARAGRAPH = "paragraph"    # Level 2: Paragraph-level embeddings
    SENTENCE = "sentence"      # Level 3: Sentence-level embeddings
    CONCEPT = "concept"        # Level 4: LLM concept analysis
```

### Data Model Progression
```python
# Level 1: Document
{
    "document_id": "doc_001",
    "embedding": [0.1, 0.2, ...],
    "metadata": {...}
}

# Level 2: Paragraph
{
    "document_id": "doc_001",
    "paragraph_id": "p_001",
    "embedding": [0.1, 0.2, ...],
    "metadata": {...},
    "paragraph_text": "..."
}

# Level 3: Sentence
{
    "document_id": "doc_001",
    "paragraph_id": "p_001",
    "sentence_id": "s_001",
    "embedding": [0.1, 0.2, ...],
    "metadata": {...},
    "sentence_text": "..."
}

# Level 4: Concept
{
    "document_id": "doc_001",
    "paragraph_id": "p_001",
    "concepts": [
        {
            "concept_id": "vef_logical_construction",
            "confidence": 0.89,
            "evidence": "...",
            "vef_category": "Framework_Core"
        }
    ]
}
```

## Implementation Strategy

### Phase 1: Document Level (Current Priority)
**Goal**: Fix ChromaDB metadata corruption, enable basic analysis
**Implementation**: 
- Fix `run_full_analysis()` method
- Clean metadata for ChromaDB storage
- Enable document-level clustering and search

### Phase 2: Paragraph Level (Future)
**Goal**: Enable paragraph-level analysis for detailed content discovery
**Implementation**:
- Text chunking logic for paragraph extraction
- Paragraph-level embedding generation
- Paragraph-specific search and clustering

### Phase 3: Sentence Level (Future)
**Goal**: Enable sentence-level precision for exact content matching
**Implementation**:
- Sentence segmentation logic
- Sentence-level embedding generation
- Fine-grained search capabilities

### Phase 4: Concept Level (Future)
**Goal**: LLM-enhanced VEF Framework concept mapping
**Implementation**:
- LLM integration for concept analysis
- VEF Framework concept taxonomy
- Concept-based navigation and categorization

## CLI Interface Design

### Current Implementation (Level 1)
```bash
python analyze.py analyze
# Returns document-level analysis
```

### Future Implementation (All Levels)
```bash
python analyze.py analyze --detail-level document
python analyze.py analyze --detail-level paragraph
python analyze.py analyze --detail-level sentence
python analyze.py analyze --detail-level concept
```

### JSON Response Structure
```json
{
  "success": true,
  "processing_time": 45.2,
  "detail_level": "document",
  "analysis": {
    "documents_processed": 448,
    "embeddings_generated": 448,
    "clusters_created": 9,
    "cross_references_found": 1247,
    "granularity_stats": {
      "document_level": 448,
      "paragraph_level": 0,
      "sentence_level": 0,
      "concept_level": 0
    }
  }
}
```

## Database Schema Evolution

### Current Schema (Level 1)
```sql
-- documents table (exists)
-- chroma_embeddings (document-level)
-- clusters (document-level)
```

### Future Schema (Progressive Levels)
```sql
-- Level 2: Paragraph embeddings
CREATE TABLE paragraph_embeddings (
    id INTEGER PRIMARY KEY,
    document_id TEXT,
    paragraph_index INTEGER,
    embedding_id TEXT,
    text_content TEXT,
    metadata JSON
);

-- Level 3: Sentence embeddings
CREATE TABLE sentence_embeddings (
    id INTEGER PRIMARY KEY,
    document_id TEXT,
    paragraph_id INTEGER,
    sentence_index INTEGER,
    embedding_id TEXT,
    text_content TEXT,
    metadata JSON
);

-- Level 4: Concept mappings
CREATE TABLE concept_mappings (
    id INTEGER PRIMARY KEY,
    document_id TEXT,
    paragraph_id INTEGER,
    concept_id TEXT,
    vef_category TEXT,
    confidence REAL,
    evidence TEXT,
    llm_analysis JSON
);
```

## Performance Considerations

### Level 1: Document (448 documents)
- **Embeddings**: 448 vectors
- **Processing Time**: ~45 seconds
- **Memory**: Low
- **Storage**: ~2MB

### Level 2: Paragraph (estimated 4,000 paragraphs)
- **Embeddings**: ~4,000 vectors
- **Processing Time**: ~6 minutes
- **Memory**: Medium
- **Storage**: ~20MB

### Level 3: Sentence (estimated 20,000 sentences)
- **Embeddings**: ~20,000 vectors
- **Processing Time**: ~30 minutes
- **Memory**: High
- **Storage**: ~100MB

### Level 4: Concept (LLM-enhanced)
- **LLM Calls**: ~4,000 paragraph analyses
- **Processing Time**: ~2 hours (depends on LLM speed)
- **Memory**: Medium
- **Storage**: ~50MB (concept data)

## User Experience Design

### Progressive Enhancement UI
```
Analysis Detail Level: [Document] [Paragraph] [Sentence] [Concept]
                         ●         ○          ○         ○

Processing: Document-level analysis (Level 1/4)
Time: ~45 seconds
Results: 448 documents, 9 clusters
```

### Search Capabilities by Level
```python
# Level 1: Document search
search_documents("VEF Framework")

# Level 2: Paragraph search
search_paragraphs("logical construction")

# Level 3: Sentence search
search_sentences("authority patterns")

# Level 4: Concept search
search_concepts("Framework_Core")
```

## VEF Framework Integration

### Level 1: Document Categories
- Documents classified into 9 VEF themes
- Basic document relationship analysis
- High-level framework navigation

### Level 2: Paragraph Concepts
- Paragraphs mapped to VEF concepts
- Cross-document concept linking
- Detailed framework exploration

### Level 3: Sentence Precision
- Exact quote and citation support
- Precise concept evidence
- Fine-grained framework analysis

### Level 4: Concept Taxonomy
- LLM-verified VEF concept classification
- Automated concept relationship mapping
- Framework consistency analysis

## Current Focus: Level 1 Implementation

For the immediate `analyze` command implementation, we focus on:

1. **Fix ChromaDB Metadata**: Enable document-level storage
2. **Document-Level Analysis**: 448 documents → 9 clusters
3. **Basic Search**: Document similarity and concept search
4. **Foundation**: Prepare architecture for future levels

The progressive detail system ensures users can choose their analysis granularity based on their needs, from quick document sorting to detailed philosophical concept analysis.

## Migration Path

### Phase 1: Document Level (Current)
- Implement and stabilize document-level analysis
- Fix all ChromaDB metadata issues
- Enable basic clustering and search

### Phase 2: Paragraph Level (Next)
- Add paragraph chunking logic
- Implement paragraph-level embeddings
- Enable paragraph-specific search

### Phase 3: Sentence Level (Later)
- Add sentence segmentation
- Implement sentence-level embeddings
- Enable precision search capabilities

### Phase 4: Concept Level (Advanced)
- Integrate LLM for concept analysis
- Build VEF Framework concept taxonomy
- Enable concept-based navigation

This architecture ensures the current implementation is not wasted effort, but rather the foundation for a sophisticated multi-level analysis system.