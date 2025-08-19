#!/usr/bin/env python3
"""
Performance Optimization Integration Test

Tests the comprehensive performance optimization implementation including:
- In-process caching system
- Performance monitoring
- Cache integration with services
- Middleware functionality
"""

import asyncio
import time
import logging
from typing import Dict, Any

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_cache_system():
    """Test the in-process cache system"""
    logger.info("Testing in-process cache system...")
    
    from services.cache import InProcessCache, cache_manager
    
    # Test basic cache operations
    cache = cache_manager.get_cache(
        "test_cache",
        max_size_mb=10,
        max_entries=100,
        default_ttl_seconds=60
    )
    
    # Test set and get
    await cache.set("test_key", {"data": "test_value", "number": 42})
    result = await cache.get("test_key")
    assert result is not None
    assert result["data"] == "test_value"
    assert result["number"] == 42
    
    # Test TTL expiration
    await cache.set("ttl_key", "ttl_value", ttl_seconds=1)
    await asyncio.sleep(1.1)
    expired_result = await cache.get("ttl_key")
    assert expired_result is None
    
    # Test cache metrics
    metrics = cache.get_metrics()
    assert "hits" in metrics
    assert "misses" in metrics
    assert "total_size_mb" in metrics
    
    logger.info("Cache system test passed ✓")
    return True


async def test_presets_caching():
    """Test presets service caching integration"""
    logger.info("Testing presets service caching...")
    
    from services.presets import list_presets, get_preset
    
    try:
        # Test cached presets list
        start_time = time.time()
        presets_list = await list_presets()
        first_call_time = time.time() - start_time
        
        # Second call should be faster (cached)
        start_time = time.time()
        cached_presets_list = await list_presets()
        second_call_time = time.time() - start_time
        
        assert len(presets_list) == len(cached_presets_list)
        logger.info(f"Presets list - First call: {first_call_time:.3f}s, Second call: {second_call_time:.3f}s")
        
        # Test individual preset caching if presets exist
        if presets_list:
            preset_id = presets_list[0]["id"]
            
            start_time = time.time()
            preset = await get_preset(preset_id)
            first_preset_time = time.time() - start_time
            
            start_time = time.time()
            cached_preset = await get_preset(preset_id)
            second_preset_time = time.time() - start_time
            
            assert preset.id == cached_preset.id
            logger.info(f"Preset get - First call: {first_preset_time:.3f}s, Second call: {second_preset_time:.3f}s")
        
        logger.info("Presets caching test passed ✓")
        return True
        
    except Exception as e:
        logger.error(f"Presets caching test failed: {e}")
        return False


async def test_framework_caching():
    """Test framework metadata caching"""
    logger.info("Testing framework metadata caching...")
    
    from services.framework_cache import get_framework_metadata, list_available_frameworks
    
    try:
        # Test frameworks list caching
        frameworks = await list_available_frameworks()
        assert isinstance(frameworks, list)
        assert len(frameworks) > 0
        
        # Test individual framework metadata
        if frameworks:
            framework_id = frameworks[0]["id"]
            metadata = await get_framework_metadata(framework_id)
            assert metadata is not None
            assert metadata["id"] == framework_id
        
        logger.info("Framework caching test passed ✓")
        return True
        
    except Exception as e:
        logger.error(f"Framework caching test failed: {e}")
        return False


async def test_performance_monitoring():
    """Test performance monitoring service"""
    logger.info("Testing performance monitoring...")
    
    from services.performance import (
        performance_monitor, 
        get_performance_statistics,
        QueryMetrics,
        RequestMetrics
    )
    
    try:
        # Test query metrics recording
        query_metrics = QueryMetrics(
            query_type="test_query",
            execution_time_ms=150.5,
            ru_consumed=25.0,
            rows_returned=10,
            correlation_id="test-correlation-id"
        )
        performance_monitor.record_query_metrics(query_metrics)
        
        # Test request metrics recording
        request_metrics = RequestMetrics(
            method="GET",
            path="/api/test",
            status_code=200,
            execution_time_ms=250.0,
            cache_hits=2,
            cache_misses=1,
            correlation_id="test-correlation-id"
        )
        performance_monitor.record_request_metrics(request_metrics)
        
        # Test performance statistics
        stats = get_performance_statistics(time_window_minutes=1)
        assert stats.total_requests >= 1
        assert stats.total_db_queries >= 1
        
        logger.info("Performance monitoring test passed ✓")
        return True
        
    except Exception as e:
        logger.error(f"Performance monitoring test failed: {e}")
        return False


async def test_cache_metrics():
    """Test cache metrics collection"""
    logger.info("Testing cache metrics collection...")
    
    from services.cache import get_cache_metrics, cache_manager
    
    try:
        # Create some cache activity
        cache = cache_manager.get_cache("metrics_test", max_size_mb=5)
        
        # Generate some hits and misses
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Hit
        await cache.get("key3")  # Miss
        
        # Get metrics
        metrics = get_cache_metrics()
        assert "metrics_test" in metrics
        
        test_metrics = metrics["metrics_test"]
        assert test_metrics["hits"] >= 2
        assert test_metrics["misses"] >= 1
        assert test_metrics["entry_count"] >= 2
        
        logger.info("Cache metrics test passed ✓")
        return True
        
    except Exception as e:
        logger.error(f"Cache metrics test failed: {e}")
        return False


async def test_configuration():
    """Test configuration loading"""
    logger.info("Testing configuration...")
    
    from config import config
    
    try:
        # Test cache configuration
        assert hasattr(config, "cache")
        assert hasattr(config.cache, "enabled")
        assert hasattr(config.cache, "presets_ttl_seconds")
        
        # Test performance configuration
        assert hasattr(config, "performance")
        assert hasattr(config.performance, "enable_request_timing")
        assert hasattr(config.performance, "slow_request_threshold_ms")
        
        logger.info("Configuration test passed ✓")
        return True
        
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False


async def run_integration_test():
    """Run complete integration test suite"""
    logger.info("Starting performance optimization integration tests...")
    
    test_results = {}
    
    # Run all tests
    tests = [
        ("Configuration", test_configuration),
        ("Cache System", test_cache_system),
        ("Cache Metrics", test_cache_metrics),
        ("Performance Monitoring", test_performance_monitoring),
        ("Presets Caching", test_presets_caching),
        ("Framework Caching", test_framework_caching),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results[test_name] = "PASSED" if result else "FAILED"
        except Exception as e:
            logger.error(f"{test_name} test error: {e}")
            test_results[test_name] = "ERROR"
    
    # Print results summary
    logger.info("\n" + "="*50)
    logger.info("INTEGRATION TEST RESULTS")
    logger.info("="*50)
    
    passed_count = 0
    total_count = len(test_results)
    
    for test_name, status in test_results.items():
        status_symbol = "✓" if status == "PASSED" else "✗"
        logger.info(f"{status_symbol} {test_name}: {status}")
        if status == "PASSED":
            passed_count += 1
    
    logger.info("="*50)
    logger.info(f"SUMMARY: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        logger.info("🎉 ALL TESTS PASSED! Performance optimization implementation is working correctly.")
        return True
    else:
        logger.warning(f"⚠️  {total_count - passed_count} test(s) failed. Please review the implementation.")
        return False


async def main():
    """Main test entry point"""
    try:
        success = await run_integration_test()
        exit_code = 0 if success else 1
        
        # Cleanup
        from services.cache import cache_manager
        await cache_manager.stop_all_cleanup()
        
        exit(exit_code)
        
    except Exception as e:
        logger.error(f"Integration test failed with error: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())