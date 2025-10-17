#!/usr/bin/env python3
"""
tools/search_docs.py
Semantic documentation search tool with daemon mode.

Standalone tool - no framework dependencies.
Search indexed documentation using semantic similarity.

Usage:
    # Daemon mode (keeps model loaded)
    python tools/search_docs.py --daemon          # Start daemon
    python tools/search_docs.py "query"           # Fast search via daemon
    python tools/search_docs.py --stop            # Stop daemon

    # Direct mode (loads model each time)
    python tools/search_docs.py "query" --direct
    python tools/search_docs.py "query" --top 10 --preview
"""

import sys
import argparse
import socket
import json
import os
import signal
import time
from pathlib import Path

# Lazy imports to avoid hanging on sentence_transformers import
# sentence_transformers can hang during import if CUDA/model cache is locked
# Import only when actually needed in functions


# Configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_CACHE_DIR = "data/models/"  # Matches framework default
INDEX_PATH = Path(__file__).parent / ".doc_index" / "chromadb"
COLLECTION_NAME = "framework_docs"

# Daemon configuration - unique per codebase
# Use hash of absolute path to allow multiple codebases to run daemons simultaneously
import hashlib
_docs_abs_path = str(Path(__file__).parent.resolve())
_path_hash = hashlib.md5(_docs_abs_path.encode()).hexdigest()[:8]
SOCKET_PATH = f"/tmp/doc_search_daemon_{_path_hash}.sock"
PID_FILE = Path(__file__).parent / ".doc_index" / f"daemon_{_path_hash}.pid"
LOG_FILE = Path(__file__).parent / ".doc_index" / f"daemon_{_path_hash}.log"


def check_daemon_running():
    """Check if daemon is running."""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        # Process doesn't exist, clean up stale files
        if PID_FILE.exists():
            PID_FILE.unlink()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
        return False


def start_daemon(foreground=False):
    """Start daemon mode - load model once and listen for queries.

    Args:
        foreground: If True, run in foreground with output to terminal.
                   If False, fork to background and log to file.
    """
    # Check if daemon already running
    if check_daemon_running():
        print("Error: Daemon is already running")
        print(f"PID: {PID_FILE.read_text().strip()}")
        print(f"Log: {LOG_FILE}")
        print()
        print("Use 'python tools/search_docs.py --stop' to stop it")
        sys.exit(1)

    # Check if index exists
    if not INDEX_PATH.exists():
        print("Error: Documentation index not found!")
        print()
        print("Please build the index first:")
        print("  python tools/rebuild_index.py")
        sys.exit(1)

    # If background mode, fork process
    if not foreground:
        pid = os.fork()
        if pid > 0:
            # Parent process - wait for child to start and create socket
            max_wait = 10  # seconds
            waited = 0
            while waited < max_wait:
                time.sleep(0.5)
                waited += 0.5
                # Check if socket exists (daemon is ready)
                if os.path.exists(SOCKET_PATH) and check_daemon_running():
                    child_pid = PID_FILE.read_text().strip()
                    print(f"Daemon started successfully!")
                    print(f"PID: {child_pid}")
                    print(f"Socket: {SOCKET_PATH}")
                    print(f"Log: {LOG_FILE}")
                    print()
                    print("Use 'python tools/search_docs.py --status' to check status")
                    print("Use 'python tools/search_docs.py --stop' to stop daemon")
                    sys.exit(0)

            # Timeout - daemon didn't start
            print("Error: Daemon failed to start. Check log file:")
            print(f"  tail -f {LOG_FILE}")
            sys.exit(1)

        # Child process continues - redirect output to log file
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log_fd = os.open(str(LOG_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        os.dup2(log_fd, sys.stdout.fileno())
        os.dup2(log_fd, sys.stderr.fileno())
        os.close(log_fd)

    # Lazy import - only load when starting daemon
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    print("Starting documentation search daemon...", flush=True)
    print(flush=True)

    # Load model
    print(f"Loading model: {MODEL_NAME}", flush=True)
    model = SentenceTransformer(MODEL_NAME, cache_folder=MODEL_CACHE_DIR)
    print(f"Model loaded (dimension: {model.get_sentence_embedding_dimension()})", flush=True)

    # Load ChromaDB
    print(f"Loading index: {INDEX_PATH}", flush=True)
    client = chromadb.PersistentClient(
        path=str(INDEX_PATH),
        settings=ChromaSettings(anonymized_telemetry=False)
    )

    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"Collection loaded: {COLLECTION_NAME} ({collection.count()} chunks)", flush=True)
    except Exception as e:
        print(f"Error: Could not load collection '{COLLECTION_NAME}'", flush=True)
        print(f"Details: {e}", flush=True)
        sys.exit(1)

    # Create Unix socket
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(SOCKET_PATH)
    sock.listen(5)

    # Save PID
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    print()
    print("=" * 50)
    print(f"Daemon started successfully!")
    print(f"PID: {os.getpid()}")
    print(f"Socket: {SOCKET_PATH}")
    print()
    print("Usage:")
    print("  python tools/search_docs.py 'your query'")
    print("  python tools/search_docs.py --stop")
    print("=" * 50)
    print()
    print("Ready to accept queries (Ctrl+C to stop)...")
    print()

    # Handle termination signals
    def signal_handler(signum, frame):
        print("\n\nShutting down daemon...")
        sock.close()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
        if PID_FILE.exists():
            PID_FILE.unlink()
        print("Daemon stopped")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Main daemon loop
    request_count = 0
    try:
        while True:
            print(f"Waiting for connection...", flush=True)
            conn, _ = sock.accept()
            print(f"Connection accepted", flush=True)

            try:
                # Receive query data
                print(f"Receiving data...", flush=True)
                data = conn.recv(8192).decode('utf-8')
                print(f"Received {len(data)} bytes", flush=True)
                query_data = json.loads(data)
                print(f"Parsed JSON: {query_data}", flush=True)

                command = query_data.get('command', 'search')

                if command == 'stop':
                    # Graceful shutdown
                    response = {"status": "stopping"}
                    conn.send(json.dumps(response).encode('utf-8'))
                    conn.close()
                    break

                elif command == 'search':
                    query = query_data.get('query', '')
                    top_k = query_data.get('top_k', 5)

                    request_count += 1
                    print(f"[{request_count}] Query: '{query}' (top {top_k})", flush=True)

                    # Generate embedding
                    print(f"Generating embedding...", flush=True)
                    query_embedding = model.encode(query, convert_to_numpy=True)
                    print(f"Embedding generated", flush=True)

                    # Search
                    print(f"Searching collection...", flush=True)
                    results = collection.query(
                        query_embeddings=[query_embedding.tolist()],
                        n_results=top_k,
                        include=["metadatas", "documents", "distances"]
                    )
                    print(f"Search complete", flush=True)

                    # Format results
                    response = {
                        "status": "success",
                        "query": query,
                        "results": {
                            "ids": results['ids'][0],
                            "distances": results['distances'][0],
                            "metadatas": results['metadatas'][0],
                            "documents": results['documents'][0]
                        }
                    }

                    # Send results
                    response_json = json.dumps(response)
                    print(f"Sending response ({len(response_json)} bytes)...", flush=True)
                    conn.send(response_json.encode('utf-8'))
                    print(f"Response sent", flush=True)

                else:
                    response = {"status": "error", "message": f"Unknown command: {command}"}
                    conn.send(json.dumps(response).encode('utf-8'))

            except Exception as e:
                print(f"Error in request handling: {e}", flush=True)
                import traceback
                traceback.print_exc()
                response = {"status": "error", "message": str(e)}
                try:
                    conn.send(json.dumps(response).encode('utf-8'))
                except:
                    pass

            finally:
                conn.close()
                print(f"Connection closed", flush=True)

    finally:
        signal_handler(None, None)


def stop_daemon():
    """Stop the daemon process."""
    if not check_daemon_running():
        print("No daemon is running")
        return

    try:
        # Try graceful stop via socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        stop_command = json.dumps({"command": "stop"})
        sock.send(stop_command.encode('utf-8'))
        response = json.loads(sock.recv(1024).decode('utf-8'))
        sock.close()

        # Wait for cleanup
        time.sleep(0.5)

        print("Daemon stopped successfully")

    except Exception:
        # Fallback to SIGTERM
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            print(f"Daemon stopped (PID: {pid})")
        except Exception as e:
            print(f"Error stopping daemon: {e}")

    finally:
        # Clean up files
        if PID_FILE.exists():
            PID_FILE.unlink()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)


def search_via_daemon(query: str, top_k: int = 5, show_preview: bool = False):
    """Search via daemon (fast - model already loaded)."""

    if not check_daemon_running():
        print("Error: Daemon is not running")
        print()
        print("Start the daemon first:")
        print("  python tools/search_docs.py --daemon")
        print()
        print("Or use direct mode:")
        print("  python tools/search_docs.py 'query' --direct")
        sys.exit(1)

    try:
        # Connect to daemon
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)

        # Send query
        query_data = json.dumps({
            "command": "search",
            "query": query,
            "top_k": top_k
        })
        sock.send(query_data.encode('utf-8'))

        # Receive results
        response_data = sock.recv(65536).decode('utf-8')
        response = json.loads(response_data)
        sock.close()

        if response['status'] != 'success':
            print(f"Error: {response.get('message', 'Unknown error')}")
            sys.exit(1)

        # Display results
        display_results(response['results'], query, show_preview)

    except Exception as e:
        print(f"Error communicating with daemon: {e}")
        print()
        print("Try restarting the daemon:")
        print("  python tools/search_docs.py --stop")
        print("  python tools/search_docs.py --daemon")
        sys.exit(1)


def search_direct(query: str, top_k: int = 5, show_preview: bool = False):
    """Direct search (loads model each time)."""
    # Lazy import - only load when doing direct search
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    # Check if index exists
    if not INDEX_PATH.exists():
        print("Error: Documentation index not found!")
        print()
        print("Please build the index first:")
        print("  python tools/rebuild_index.py")
        sys.exit(1)

    # Load model
    print(f"Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME, cache_folder=MODEL_CACHE_DIR)

    # Load ChromaDB
    client = chromadb.PersistentClient(
        path=str(INDEX_PATH),
        settings=ChromaSettings(anonymized_telemetry=False)
    )

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Error: Could not load collection '{COLLECTION_NAME}'")
        print(f"Details: {e}")
        sys.exit(1)

    # Generate embedding and search
    query_embedding = model.encode(query, convert_to_numpy=True)
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        include=["metadatas", "documents", "distances"]
    )

    # Display results
    display_results(results, query, show_preview)


def display_results(results, query, show_preview=False):
    """Display search results in formatted output."""

    print()
    print("=" * 70)
    print(f"Search: '{query}'")
    print("=" * 70)
    print()

    # Handle both direct ChromaDB results (nested lists) and daemon results (flat lists)
    ids = results['ids'][0] if isinstance(results['ids'][0], list) else results['ids']
    distances = results['distances'][0] if isinstance(results['distances'][0], list) else results['distances']
    metadatas = results['metadatas'][0] if isinstance(results['metadatas'][0], list) else results['metadatas']
    documents = results['documents'][0] if isinstance(results['documents'][0], list) else results['documents']

    if not ids:
        print("No results found.")
        print()
        return

    for i, (doc_id, distance, metadata, document) in enumerate(zip(ids, distances, metadatas, documents), 1):
        # Convert distance to similarity score
        similarity = 1 - distance

        # Display result
        file_path = metadata['file_path']
        section_title = metadata.get('section_title')
        line_start = metadata.get('line_start')
        line_count = metadata.get('line_count')

        # Build location string with line number support
        if line_start:
            location = f"{file_path}:{line_start}"
        else:
            location = file_path

        if section_title:
            print(f"{i}. {location} >> {section_title}")
        else:
            print(f"{i}. {location}")

        print(f"   Similarity: {similarity:.3f}")

        # Show line count if available
        if line_count:
            print(f"   Lines: {line_count} ({metadata.get('size_bytes', 0):,} bytes)")
        else:
            print(f"   Size: {metadata.get('size_bytes', 0):,} bytes")

        if show_preview:
            print(f"   Preview: {document[:200]}...")

        print()

    print("=" * 70)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Search framework documentation semantically",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Daemon Mode (Recommended):
  python tools/search_docs.py --daemon          # Start daemon (loads model once)
  python tools/search_docs.py "your query"      # Fast search via daemon
  python tools/search_docs.py --stop            # Stop daemon

Direct Mode:
  python tools/search_docs.py "query" --direct  # Load model each time
  python tools/search_docs.py "query" --top 10 --preview

Examples:
  # Start daemon
  python tools/search_docs.py --daemon

  # Search (uses daemon if running, otherwise prompts to start)
  python tools/search_docs.py "how to register models"
  python tools/search_docs.py "database session" --top 10
  python tools/search_docs.py "pydantic settings" --preview

  # Stop daemon
  python tools/search_docs.py --stop
        """
    )

    parser.add_argument(
        'query',
        nargs='*',
        help='Search query (multiple words combined into one query)'
    )

    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Start daemon mode (keeps model loaded, runs in background)'
    )

    parser.add_argument(
        '--tail',
        action='store_true',
        help='Run daemon in foreground with output to terminal (use with --daemon)'
    )

    parser.add_argument(
        '--stop',
        action='store_true',
        help='Stop daemon'
    )

    parser.add_argument(
        '--direct',
        action='store_true',
        help='Use direct mode (load model each time, bypass daemon)'
    )

    parser.add_argument(
        '--top', '-t',
        type=int,
        default=5,
        help='Number of results to return (default: 5)'
    )

    parser.add_argument(
        '--preview', '-p',
        action='store_true',
        help='Show content preview for each result'
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Check daemon status'
    )

    args = parser.parse_args()

    # Handle daemon commands
    if args.daemon:
        # --tail makes daemon run in foreground
        start_daemon(foreground=args.tail)
        return

    if args.stop:
        stop_daemon()
        return

    if args.status:
        if check_daemon_running():
            pid = PID_FILE.read_text().strip()
            print(f"Daemon is running (PID: {pid})")
            print(f"Socket: {SOCKET_PATH}")
        else:
            print("Daemon is not running")
        return

    # Handle search
    if not args.query:
        parser.print_help()
        return

    query = " ".join(args.query)

    if args.direct:
        # Direct mode - load model each time
        search_direct(query, top_k=args.top, show_preview=args.preview)
    else:
        # Try daemon mode first
        search_via_daemon(query, top_k=args.top, show_preview=args.preview)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
