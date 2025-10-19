"""
Test script to verify embedding cache format consistency fix.

This test verifies that cached embeddings return the same format as fresh embeddings.
Bug: Cache was unwrapping single embeddings from [[embedding]] to [embedding]
Fix: Always return list of embeddings, never unwrap
"""

import asyncio
import sys
from modules.core.model_manager.cache.embedding_cache import EmbeddingCache
from modules.core.model_manager.settings import ModelManagerSettings


async def test_cache_format_consistency():
    """Test that cache returns same format as fresh results."""
    print("Testing embedding cache format consistency...")

    # Create cache with default settings
    settings = ModelManagerSettings()
    cache = EmbeddingCache(settings)

    # Simulate embedding results
    test_text = "test query"
    model_id = "test-model"

    # Fresh embedding format: list containing one embedding list
    fresh_embedding = [[0.347, 0.280, 0.123, 0.456]]  # 4 dimensions for testing

    # Cache the embedding
    await cache.cache_embeddings(test_text, fresh_embedding, model_id)
    print(f"Cached embedding: {fresh_embedding}")

    # Retrieve from cache
    result = await cache.get_embeddings(test_text, model_id)

    if not result.success:
        print(f"ERROR: Cache retrieval failed: {result.message}")
        return False

    cached_embeddings = result.data.get("embeddings", [])

    # Verify format consistency
    print(f"\nFormat verification:")
    print(f"Fresh format:  type={type(fresh_embedding)}, len={len(fresh_embedding)}")
    print(f"               first element type={type(fresh_embedding[0])}, len={len(fresh_embedding[0])}")
    print(f"Cached format: type={type(cached_embeddings)}, len={len(cached_embeddings)}")
    print(f"               first element type={type(cached_embeddings[0])}, len={len(cached_embeddings[0])}")

    # Check if formats match
    if isinstance(cached_embeddings[0], list):
        print("\nSUCCESS: Cache returns list of embeddings (correct format)")
        print(f"Fresh:  embeddings[0] = {fresh_embedding[0][:3]}... (embedding vector)")
        print(f"Cached: embeddings[0] = {cached_embeddings[0][:3]}... (embedding vector)")

        # Verify actual content matches
        if cached_embeddings == fresh_embedding:
            print("\nSUCCESS: Cached content matches fresh content exactly")
            return True
        else:
            print("\nERROR: Content mismatch!")
            return False
    else:
        print(f"\nERROR: Cache returns flat embedding (bug not fixed!)")
        print(f"Fresh:  embeddings[0] = {fresh_embedding[0][:3]}... (embedding vector)")
        print(f"Cached: embeddings[0] = {cached_embeddings[0]} (just a float!)")
        return False


async def test_multiple_embeddings():
    """Test cache with multiple embeddings."""
    print("\n" + "="*60)
    print("Testing multiple embeddings...")

    settings = ModelManagerSettings()
    cache = EmbeddingCache(settings)

    # Multiple texts
    test_texts = ["query 1", "query 2", "query 3"]
    model_id = "test-model"

    # Fresh embeddings: list of embedding lists
    fresh_embeddings = [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
        [0.9, 1.0, 1.1, 1.2]
    ]

    # Cache all embeddings
    await cache.cache_embeddings(test_texts, fresh_embeddings, model_id)
    print(f"Cached {len(fresh_embeddings)} embeddings")

    # Retrieve from cache
    result = await cache.get_embeddings(test_texts, model_id)

    if not result.success:
        print(f"ERROR: Cache retrieval failed: {result.message}")
        return False

    cached_embeddings = result.data.get("embeddings", [])

    # Verify format
    print(f"\nFormat verification:")
    print(f"Fresh:  {len(fresh_embeddings)} embeddings, each length {len(fresh_embeddings[0])}")
    print(f"Cached: {len(cached_embeddings)} embeddings, each length {len(cached_embeddings[0])}")

    if cached_embeddings == fresh_embeddings:
        print("\nSUCCESS: Multiple embeddings cached and retrieved correctly")
        return True
    else:
        print("\nERROR: Content mismatch!")
        return False


async def main():
    """Run all cache tests."""
    print("="*60)
    print("Embedding Cache Format Consistency Test")
    print("="*60)

    # Test single embedding (the bug scenario)
    test1_passed = await test_cache_format_consistency()

    # Test multiple embeddings
    test2_passed = await test_multiple_embeddings()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Single embedding test:   {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Multiple embeddings test: {'PASSED' if test2_passed else 'FAILED'}")

    if test1_passed and test2_passed:
        print("\nALL TESTS PASSED - Cache format fix verified!")
        return 0
    else:
        print("\nSOME TESTS FAILED - Cache format issue detected!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
