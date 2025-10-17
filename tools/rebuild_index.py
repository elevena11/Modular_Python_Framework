#!/usr/bin/env python3
"""
tools/rebuild_index.py
Rebuild documentation search index.

Standalone tool - no framework dependencies.
Scans all .md files in docs/ and creates ChromaDB index for semantic search.

Usage:
    python tools/rebuild_index.py
"""

from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings


# Configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_CACHE_DIR = "data/models/"  # Matches framework default
INDEX_PATH = Path(__file__).parent / ".doc_index" / "chromadb"
COLLECTION_NAME = "framework_docs"

# Chunking strategy: "whole" or "sections"
CHUNKING_STRATEGY = "sections"  # Change to "whole" for Option A


def split_into_sections(content: str, file_path: str):
    """
    Split markdown content into sections based on headings.

    Returns list of (section_id, section_title, section_content, line_start, line_count) tuples.
    """
    import re

    sections = []
    lines = content.split('\n')

    current_section = []
    current_heading = "Introduction"
    section_num = 0
    section_start_line = 1  # Line numbers are 1-indexed

    for line_idx, line in enumerate(lines, start=1):
        # Match markdown headings (## or ###)
        heading_match = re.match(r'^(#{2,3})\s+(.+)$', line)

        if heading_match:
            # Save previous section if it has content
            if current_section:
                section_content = '\n'.join(current_section).strip()
                if section_content:
                    section_id = f"{file_path}#section{section_num}"
                    line_count = len(current_section)
                    sections.append((section_id, current_heading, section_content, section_start_line, line_count))
                    section_num += 1

            # Start new section
            current_heading = heading_match.group(2).strip()
            current_section = [line]  # Include heading in content
            section_start_line = line_idx
        else:
            current_section.append(line)

    # Add final section
    if current_section:
        section_content = '\n'.join(current_section).strip()
        if section_content:
            section_id = f"{file_path}#section{section_num}"
            line_count = len(current_section)
            sections.append((section_id, current_heading, section_content, section_start_line, line_count))

    return sections


def rebuild_index():
    """Scan docs/ directory and rebuild ChromaDB index."""
    print("Documentation Index Builder")
    print("=" * 50)
    print(f"Model: {MODEL_NAME}")
    print(f"Chunking: {CHUNKING_STRATEGY}")
    print(f"Index: {INDEX_PATH}")
    print()

    # Initialize model
    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME, cache_folder=MODEL_CACHE_DIR)
    print(f"Model loaded (dimension: {model.get_sentence_embedding_dimension()})")
    print()

    # Initialize ChromaDB
    print("Initializing ChromaDB...")
    INDEX_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(INDEX_PATH),
        settings=ChromaSettings(anonymized_telemetry=False)
    )

    # Recreate collection (fresh index)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection: {COLLECTION_NAME}")
    except:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # Cosine similarity
    )
    print(f"Created collection: {COLLECTION_NAME}")
    print()

    # Find all markdown files in docs/ directory
    project_root = Path(__file__).parent.parent  # Parent of tools/
    docs_dir = project_root / "docs"
    markdown_files = []

    if not docs_dir.exists():
        print(f"Error: docs/ directory not found at {docs_dir}")
        return

    for md_file in docs_dir.rglob("*.md"):
        # Skip hidden directories (like .doc_index)
        if any(part.startswith('.') for part in md_file.parts):
            continue
        markdown_files.append(md_file)

    print(f"Found {len(markdown_files)} markdown files")
    print()

    # Index each file
    print("Indexing documents:")
    print("-" * 50)

    total_chunks = 0

    for i, md_file in enumerate(markdown_files, 1):
        try:
            # Read content
            content = md_file.read_text(encoding='utf-8')

            # Skip empty files
            if not content.strip():
                print(f"[{i}/{len(markdown_files)}] SKIP (empty): {md_file.name}")
                continue

            # Generate relative path (include docs/ prefix)
            relative_path = md_file.relative_to(project_root)

            if CHUNKING_STRATEGY == "sections":
                # Split into sections
                sections = split_into_sections(content, str(relative_path))

                if not sections:
                    # Fallback to whole document if no sections found
                    total_lines = content.count('\n') + 1
                    sections = [(str(relative_path), "Full Document", content, 1, total_lines)]

                # Index each section
                for section_id, section_title, section_content, line_start, line_count in sections:
                    embedding = model.encode(section_content, convert_to_numpy=True)

                    collection.add(
                        ids=[section_id],
                        embeddings=[embedding.tolist()],
                        metadatas=[{
                            "file_path": str(relative_path),
                            "full_path": str(md_file.absolute()),
                            "file_name": md_file.name,
                            "section_title": section_title,
                            "section_id": section_id,
                            "line_start": line_start,
                            "line_count": line_count,
                            "size_bytes": len(section_content),
                            "chunking": "sections"
                        }],
                        documents=[section_content[:500]]  # First 500 chars for preview
                    )

                    total_chunks += 1

                print(f"[{i}/{len(markdown_files)}] Indexed: {relative_path} ({len(sections)} sections)")

            else:
                # Whole document indexing (Option A)
                embedding = model.encode(content, convert_to_numpy=True)

                collection.add(
                    ids=[str(relative_path)],
                    embeddings=[embedding.tolist()],
                    metadatas=[{
                        "file_path": str(relative_path),
                        "full_path": str(md_file.absolute()),
                        "file_name": md_file.name,
                        "size_bytes": len(content),
                        "chunking": "whole"
                    }],
                    documents=[content[:500]]  # First 500 chars for preview
                )

                total_chunks += 1
                print(f"[{i}/{len(markdown_files)}] Indexed: {relative_path}")

        except Exception as e:
            print(f"[{i}/{len(markdown_files)}] ERROR: {md_file.name} - {e}")

    # Summary
    print()
    print("=" * 50)
    print(f"Index built successfully!")
    print(f"Chunking strategy: {CHUNKING_STRATEGY}")
    print(f"Files processed: {len(markdown_files)}")
    print(f"Total chunks indexed: {collection.count()}")
    print(f"Index location: {INDEX_PATH}")
    print()
    print("Usage:")
    print("  python tools/search_docs.py 'your search query'")
    print()


if __name__ == "__main__":
    try:
        rebuild_index()
    except KeyboardInterrupt:
        print("\n\nIndex building cancelled by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
