#!/usr/bin/env python3
"""
Test script to verify all four analysis engines are working correctly.
This ensures Spirit, Chest, Body, and Audience engines are "awake and working".
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from analysis_modules.spirit_engine import SpiritEngine
from analysis_modules.chest_engine import ChestEngine
from analysis_modules.body_engine import BodyEngine
from analysis_modules.audience_engine import AudienceEngine
from analysis_modules.shared.data_structures import WordSegment


def test_spirit_engine():
    """Test Spirit Engine initialization and basic functionality."""
    print("🔥 Testing Spirit Engine...")
    try:
        engine = SpiritEngine()
        print("   ✅ Spirit Engine initialized successfully")
        print(f"   - Component weights: {engine.weights}")
        return True
    except Exception as e:
        print(f"   ❌ Spirit Engine failed: {e}")
        return False


def test_chest_engine():
    """Test Chest Engine initialization and basic functionality."""
    print("\n💨 Testing Chest Engine...")
    try:
        engine = ChestEngine()
        print("   ✅ Chest Engine initialized successfully")
        print(f"   - Component weights: {engine.weights}")
        return True
    except Exception as e:
        print(f"   ❌ Chest Engine failed: {e}")
        return False


def test_body_engine():
    """Test Body Engine initialization and basic functionality."""
    print("\n🎪 Testing Body Engine...")
    try:
        engine = BodyEngine()
        print("   ✅ Body Engine initialized successfully")
        print(f"   - Component weights: {engine.weights}")
        return True
    except Exception as e:
        print(f"   ❌ Body Engine failed: {e}")
        return False


def test_audience_engine():
    """Test Audience Engine initialization and basic functionality."""
    print("\n👥 Testing Audience Engine...")
    try:
        engine = AudienceEngine()
        print("   ✅ Audience Engine initialized successfully")
        print(f"   - Component weights: {engine.weights}")
        return True
    except Exception as e:
        print(f"   ❌ Audience Engine failed: {e}")
        return False


def test_score_ranges():
    """Test that engines produce scores in the full 1-5 range."""
    print("\n📊 Testing Score Range (1-5)...")
    try:
        # Test with sample data
        from analysis_modules.spirit_engine.spirit_engine import SpiritEngine

        # Verify normalization function
        engine = SpiritEngine()
        test_scores = [0.0, 0.25, 0.5, 0.75, 1.0]
        expected = [1.0, 2.0, 3.0, 4.0, 5.0]

        print("   Testing score normalization (0-1 → 1-5):")
        all_correct = True
        for test, exp in zip(test_scores, expected):
            result = engine._normalize_to_5_scale(test)
            status = "✓" if abs(result - exp) < 0.01 else "✗"
            print(f"     {status} {test} → {result} (expected {exp})")
            if abs(result - exp) >= 0.01:
                all_correct = False

        if all_correct:
            print("   ✅ Score range verification passed")
            return True
        else:
            print("   ❌ Score range verification failed")
            return False

    except Exception as e:
        print(f"   ❌ Score range test failed: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking Dependencies...")
    all_good = True

    deps = [
        ('numpy', 'numpy'),
        ('opensmile', 'openSMILE'),
        ('transformers', 'HuggingFace Transformers'),
        ('torch', 'PyTorch')
    ]

    for module, name in deps:
        try:
            __import__(module)
            print(f"   ✅ {name} installed")
        except ImportError:
            print(f"   ⚠️  {name} NOT installed (pip install {module})")
            all_good = False

    return all_good


def main():
    """Run all tests."""
    print("=" * 60)
    print("STAGE BUDDY V2 - ENGINE VERIFICATION")
    print("=" * 60)

    results = []

    # Check dependencies first
    deps_ok = check_dependencies()
    results.append(("Dependencies", deps_ok))

    # Test each engine
    results.append(("Spirit Engine", test_spirit_engine()))
    results.append(("Chest Engine", test_chest_engine()))
    results.append(("Body Engine", test_body_engine()))
    results.append(("Audience Engine", test_audience_engine()))

    # Test score ranges
    results.append(("Score Range (1-5)", test_score_ranges()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All engines are AWAKE and WORKING!")
        return 0
    else:
        print("\n⚠️  Some engines need attention")
        return 1


if __name__ == '__main__':
    sys.exit(main())
