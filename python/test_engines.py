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
    except ImportError as e:
        print(f"   ⚠️  Spirit Engine dependencies not installed: {e}")
        print("   ℹ️  Spirit Engine requires: torch, torchaudio, speechbrain, transformers")
        print("   ℹ️  To install: pip install torch torchaudio speechbrain transformers")
        return None  # None = skipped, not failed
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
    except ImportError as e:
        print(f"   ⚠️  Chest Engine dependencies not installed: {e}")
        print("   ℹ️  Chest Engine requires: numpy, opensmile")
        return None  # Skipped
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
    except ImportError as e:
        print(f"   ⚠️  Body Engine dependencies not installed: {e}")
        print("   ℹ️  Body Engine requires: numpy, opensmile")
        return None  # Skipped
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
    except ImportError as e:
        print(f"   ⚠️  Audience Engine dependencies not installed: {e}")
        print("   ℹ️  Audience Engine requires: numpy, opensmile")
        return None  # Skipped
    except Exception as e:
        print(f"   ❌ Audience Engine failed: {e}")
        return False


def test_score_ranges():
    """Test that engines produce scores in the full 1-5 range."""
    print("\n📊 Testing Score Range (1-5)...")
    try:
        # Try Spirit Engine first (has the most complete implementation)
        try:
            from analysis_modules.spirit_engine.spirit_engine import SpiritEngine
            engine = SpiritEngine()
        except ImportError:
            # Fall back to Chest Engine if Spirit not available
            try:
                from analysis_modules.chest_engine.chest_engine import ChestEngine
                engine = ChestEngine()
            except ImportError:
                print("   ⏭️  Skipping score range test - no engines with normalization available")
                return None

        # Verify normalization function
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

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)

    for test_name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:  # None = skipped
            status = "⏭️  SKIP"
        print(f"{status} - {test_name}")

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped (out of {total} tests)")

    if failed > 0:
        print("\n❌ Some engines FAILED - check errors above")
        return 1
    elif passed == 0:
        print("\n⚠️  No engines could be tested - install dependencies")
        return 1
    else:
        if skipped > 0:
            print(f"\n✅ {passed} engines are AWAKE and WORKING! ({skipped} skipped due to missing dependencies)")
        else:
            print("\n✅ All engines are AWAKE and WORKING!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
