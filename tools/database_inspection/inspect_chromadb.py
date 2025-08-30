#!/usr/bin/env python3
"""
ChromaDB Inspection Tool
Provides direct access to ChromaDB collections for debugging and analysis.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def inspect_chromadb(persist_dir: str = "./data/llm_memory/chromadb", 
                    collection_name: Optional[str] = None,
                    show_content: bool = False,
                    limit: int = 10,
                    search_query: Optional[str] = None,
                    metadata_filter: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Inspect ChromaDB collections and return structured data.
    
    Args:
        persist_dir: Path to ChromaDB persistence directory
        collection_name: Specific collection to inspect (None for all)
        show_content: Whether to show document content
        limit: Maximum number of documents to show per collection
        search_query: Optional semantic search query
        metadata_filter: Optional metadata filter
    """
    
    try:
        import chromadb
    except ImportError:
        return {"error": "chromadb library not installed. Run: pip install chromadb"}
    
    if not os.path.exists(persist_dir):
        return {"error": f"ChromaDB directory not found: {persist_dir}"}
    
    try:
        # Create ChromaDB client
        client = chromadb.PersistentClient(path=persist_dir)
        
        # Get all collections
        collections = client.list_collections()
        
        result = {
            "persist_directory": os.path.abspath(persist_dir),
            "total_collections": len(collections),
            "collections": {}
        }
        
        for collection in collections:
            collection_info = {
                "name": collection.name,
                "count": collection.count(),
                "metadata": collection.metadata
            }
            
            # If specific collection requested and this isn't it, skip details
            if collection_name and collection.name != collection_name:
                result["collections"][collection.name] = collection_info
                continue
                
            # Get documents from collection
            if collection.count() > 0:
                if search_query:
                    # Perform semantic search
                    try:
                        search_results = collection.query(
                            query_texts=[search_query],
                            n_results=min(limit, collection.count()),
                            include=["documents", "metadatas", "distances"]
                        )
                        
                        documents = []
                        if search_results["ids"] and len(search_results["ids"]) > 0:
                            for i, doc_id in enumerate(search_results["ids"][0]):
                                doc_data = {
                                    "id": doc_id,
                                    "distance": search_results["distances"][0][i] if search_results["distances"] else None,
                                    "similarity": (1 - search_results["distances"][0][i]) if search_results["distances"] else None,
                                    "metadata": search_results["metadatas"][0][i] if search_results["metadatas"] else {}
                                }
                                
                                if show_content:
                                    doc_data["content"] = search_results["documents"][0][i] if search_results["documents"] else ""
                                else:
                                    content = search_results["documents"][0][i] if search_results["documents"] else ""
                                    doc_data["content_preview"] = content[:200] + "..." if len(content) > 200 else content
                                
                                documents.append(doc_data)
                        
                        collection_info["search_results"] = {
                            "query": search_query,
                            "documents": documents,
                            "total_found": len(documents)
                        }
                        
                    except Exception as e:
                        collection_info["search_error"] = f"Search failed: {str(e)}"
                
                else:
                    # Get sample documents
                    try:
                        sample_results = collection.peek(limit=min(limit, collection.count()))
                        
                        documents = []
                        if sample_results["ids"]:
                            for i, doc_id in enumerate(sample_results["ids"]):
                                doc_data = {
                                    "id": doc_id,
                                    "metadata": sample_results["metadatas"][i] if sample_results["metadatas"] else {}
                                }
                                
                                if show_content:
                                    doc_data["content"] = sample_results["documents"][i] if sample_results["documents"] else ""
                                else:
                                    content = sample_results["documents"][i] if sample_results["documents"] else ""
                                    doc_data["content_preview"] = content[:200] + "..." if len(content) > 200 else content
                                
                                documents.append(doc_data)
                        
                        collection_info["sample_documents"] = documents
                        
                    except Exception as e:
                        collection_info["peek_error"] = f"Failed to peek documents: {str(e)}"
            
            result["collections"][collection.name] = collection_info
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to inspect ChromaDB: {str(e)}"}

def print_inspection_results(data: Dict[str, Any], verbose: bool = False, stats_only: bool = False):
    """Print inspection results in a readable format."""
    
    if "error" in data:
        print(f"❌ Error: {data['error']}")
        return
    
    print(f"📁 ChromaDB Directory: {data['persist_directory']}")
    print(f"📊 Total Collections: {data['total_collections']}")
    print()
    
    if stats_only:
        # Show only collection statistics
        for collection_name, info in data["collections"].items():
            print(f"📦 {collection_name}: {info['count']} documents")
            if info.get("metadata"):
                for key, value in info["metadata"].items():
                    if key == "hnsw:space":
                        print(f"   Distance metric: {value}")
                    elif key == "description":
                        print(f"   Description: {value}")
        return
    
    if data['total_collections'] == 0:
        print("⚠️  No collections found in ChromaDB")
        return
    
    for collection_name, info in data["collections"].items():
        print(f"📦 Collection: {collection_name}")
        print(f"   Count: {info['count']} documents")
        
        if info.get("metadata"):
            print(f"   Metadata: {info['metadata']}")
        
        # Show search results if available
        if "search_results" in info:
            search_info = info["search_results"]
            print(f"   🔍 Search Query: '{search_info['query']}'")
            print(f"   Found: {search_info['total_found']} results")
            
            for i, doc in enumerate(search_info["documents"]):
                print(f"   📄 Result {i+1}: {doc['id']}")
                if doc.get("similarity"):
                    print(f"      Similarity: {doc['similarity']:.3f}")
                if doc.get("metadata"):
                    print(f"      Metadata: {doc['metadata']}")
                if verbose and doc.get("content"):
                    print(f"      Content: {doc['content']}")
                elif doc.get("content_preview"):
                    print(f"      Preview: {doc['content_preview']}")
                print()
        
        # Show sample documents if available
        elif "sample_documents" in info and info["sample_documents"]:
            print(f"   📄 Sample Documents (showing up to {len(info['sample_documents'])}):")
            
            for i, doc in enumerate(info["sample_documents"]):
                print(f"      {i+1}. {doc['id']}")
                if doc.get("metadata"):
                    print(f"         Metadata: {doc['metadata']}")
                if verbose and doc.get("content"):
                    print(f"         Content: {doc['content']}")
                elif doc.get("content_preview"):
                    print(f"         Preview: {doc['content_preview']}")
                print()
        
        # Show errors if any
        if "search_error" in info:
            print(f"   ❌ Search Error: {info['search_error']}")
        if "peek_error" in info:
            print(f"   ❌ Peek Error: {info['peek_error']}")
        
        print("-" * 60)

def interactive_mode(persist_dir: str):
    """Interactive mode for user-friendly database exploration."""
    print("\n📚 ChromaDB Inspector - Interactive Mode")
    print("=" * 50)
    
    # Get initial database info
    result = inspect_chromadb(persist_dir=persist_dir)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    if result['total_collections'] == 0:
        print("⚠️  No collections found in ChromaDB")
        return
    
    while True:
        # Show available collections
        print(f"\n📊 Database: {result['persist_directory']}")
        print(f"📦 Available Collections ({result['total_collections']}):")
        
        collections = list(result['collections'].items())
        for i, (name, info) in enumerate(collections, 1):
            print(f"  {i}. {name} ({info['count']} documents)")
        
        print(f"  0. Exit")
        
        # Get user choice
        try:
            choice = input(f"\nChoose collection (0-{len(collections)}): ").strip()
            
            if choice == "0" or choice.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not choice.isdigit() or int(choice) < 1 or int(choice) > len(collections):
                print("❌ Invalid choice. Please enter a number from the list.")
                continue
            
            collection_name, collection_info = collections[int(choice) - 1]
            explore_collection_interactive(persist_dir, collection_name, collection_info)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def explore_collection_interactive(persist_dir: str, collection_name: str, collection_info: dict):
    """Interactive exploration of a specific collection."""
    
    while True:
        print(f"\n📦 Collection: {collection_name}")
        print(f"📊 Documents: {collection_info['count']}")
        print("\nActions:")
        print("  1. Browse documents (preview)")
        print("  2. Browse documents (full content)")
        print("  3. Search content")
        print("  4. Show collection details")
        print("  5. Export sample data")
        print("  0. Back to collection list")
        
        try:
            action = input("\nChoose action (0-5): ").strip()
            
            if action == "0":
                break
            elif action == "1":
                browse_documents(persist_dir, collection_name, show_content=False)
            elif action == "2":
                browse_documents(persist_dir, collection_name, show_content=True)
            elif action == "3":
                search_documents(persist_dir, collection_name)
            elif action == "4":
                show_collection_details(persist_dir, collection_name)
            elif action == "5":
                export_sample_data(persist_dir, collection_name)
            else:
                print("❌ Invalid choice. Please enter a number from the menu.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def browse_documents(persist_dir: str, collection_name: str, show_content: bool = False):
    """Browse documents with pagination."""
    limit = 5
    offset = 0
    
    while True:
        print(f"\n📄 Documents in '{collection_name}' ({offset + 1}-{offset + limit}):")
        print("-" * 60)
        
        # Get documents for current page
        result = inspect_chromadb(
            persist_dir=persist_dir,
            collection_name=collection_name,
            show_content=show_content,
            limit=limit
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            break
        
        collection_data = result['collections'].get(collection_name, {})
        
        if 'sample_documents' in collection_data:
            docs = collection_data['sample_documents']
            for i, doc in enumerate(docs, offset + 1):
                print(f"\n{i}. ID: {doc['id']}")
                if doc.get('metadata'):
                    print(f"   Metadata: {doc['metadata']}")
                if show_content and doc.get('content'):
                    print(f"   Content: {doc['content'][:300]}{'...' if len(doc['content']) > 300 else ''}")
                elif doc.get('content_preview'):
                    print(f"   Preview: {doc['content_preview']}")
        
        print(f"\n📊 Showing documents {offset + 1}-{min(offset + limit, collection_data.get('count', 0))} of {collection_data.get('count', 0)}")
        print("\nNavigation:")
        print("  n = Next page")
        print("  p = Previous page") 
        print("  f = Toggle full content")
        print("  0 = Back to collection menu")
        
        nav = input("\nNavigate (n/p/f/0): ").strip().lower()
        
        if nav == "0":
            break
        elif nav == "n":
            offset += limit
        elif nav == "p":
            offset = max(0, offset - limit)
        elif nav == "f":
            show_content = not show_content
            print(f"📄 Content display: {'Full' if show_content else 'Preview'}")

def search_documents(persist_dir: str, collection_name: str):
    """Search documents interactively."""
    while True:
        query = input(f"\n🔍 Enter search query for '{collection_name}' (0 to go back): ").strip()
        
        if query == "0":
            break
        
        if not query:
            print("❌ Please enter a search query.")
            continue
        
        limit = int(input("Number of results (default 5): ") or "5")
        
        print(f"\n🔍 Searching for: '{query}'...")
        
        result = inspect_chromadb(
            persist_dir=persist_dir,
            collection_name=collection_name,
            search_query=query,
            limit=limit
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            continue
        
        collection_data = result['collections'].get(collection_name, {})
        
        if 'search_results' in collection_data:
            search_info = collection_data['search_results']
            print(f"\n📊 Found {search_info['total_found']} results:")
            
            for i, doc in enumerate(search_info['documents'], 1):
                print(f"\n{i}. ID: {doc['id']}")
                if doc.get('similarity'):
                    print(f"   Similarity: {doc['similarity']:.3f}")
                if doc.get('metadata'):
                    print(f"   Metadata: {doc['metadata']}")
                if doc.get('content_preview'):
                    print(f"   Preview: {doc['content_preview']}")
        else:
            print("❌ No search results found.")

def show_collection_details(persist_dir: str, collection_name: str):
    """Show detailed collection information."""
    result = inspect_chromadb(
        persist_dir=persist_dir,
        collection_name=collection_name,
        limit=1
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    collection_data = result['collections'].get(collection_name, {})
    
    print(f"\n📦 Collection Details: {collection_name}")
    print("=" * 50)
    print(f"📊 Document Count: {collection_data.get('count', 'Unknown')}")
    print(f"🏷️  Metadata: {collection_data.get('metadata', 'None')}")
    
    if 'sample_documents' in collection_data and collection_data['sample_documents']:
        sample_doc = collection_data['sample_documents'][0]
        if sample_doc.get('metadata'):
            print(f"\n📄 Sample Document Metadata:")
            for key, value in sample_doc['metadata'].items():
                print(f"   {key}: {value}")

def export_sample_data(persist_dir: str, collection_name: str):
    """Export sample data to JSON file."""
    limit = int(input("Number of documents to export (default 10): ") or "10")
    
    result = inspect_chromadb(
        persist_dir=persist_dir,
        collection_name=collection_name,
        show_content=True,
        limit=limit
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    # Create export filename
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chromadb_export_{collection_name}_{timestamp}.json"
    
    try:
        import json
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"✅ Exported {limit} documents to: {filename}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Inspect ChromaDB collections")
    parser.add_argument("--dir", default="./data/llm_memory/chromadb", 
                       help="ChromaDB persistence directory")
    parser.add_argument("--collection", help="Specific collection to inspect")
    parser.add_argument("--content", action="store_true", 
                       help="Show full document content")
    parser.add_argument("--limit", type=int, default=10,
                       help="Maximum documents to show per collection")
    parser.add_argument("--search", help="Semantic search query (requires matching embedding model)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--json", action="store_true",
                       help="Output as JSON")
    parser.add_argument("--stats", action="store_true",
                       help="Show detailed statistics only")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Start interactive mode")
    
    args = parser.parse_args()
    
    # Check if interactive mode
    if args.interactive:
        interactive_mode(args.dir)
        return
    
    # Original command-line functionality
    result = inspect_chromadb(
        persist_dir=args.dir,
        collection_name=args.collection,
        show_content=args.content,
        limit=args.limit,
        search_query=args.search
    )
    
    if args.json:
        import json
        print(json.dumps(result, indent=2))
    else:
        print_inspection_results(result, verbose=args.verbose, stats_only=args.stats)

if __name__ == "__main__":
    main()