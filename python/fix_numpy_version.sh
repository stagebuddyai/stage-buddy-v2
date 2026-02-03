#!/bin/bash
# Fix NumPy version compatibility issue for Numba

echo "🔧 Fixing NumPy version for Numba compatibility..."
echo ""

# Check current NumPy version
CURRENT_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "📊 Current NumPy version: $CURRENT_VERSION"

    # Check if version is 2.4 or higher
    MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
    MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)

    if [ "$MAJOR" -eq 2 ] && [ "$MINOR" -ge 4 ]; then
        echo "⚠️  NumPy $CURRENT_VERSION is too new for Numba 0.63.x"
        echo "📦 Downgrading to NumPy 2.3.x..."
        pip3 install "numpy>=2.0.0,<2.4" --force-reinstall
        echo "✅ NumPy downgraded successfully"
    else
        echo "✅ NumPy version is compatible"
    fi
else
    echo "❌ NumPy not found, installing..."
    pip3 install "numpy>=2.0.0,<2.4"
fi

echo ""
echo "🧪 Testing compatibility..."
python3 -c "
import numpy
print(f'NumPy version: {numpy.__version__}')

try:
    import numba
    print(f'Numba version: {numba.__version__}')
    print('✅ NumPy and Numba are compatible')
except ImportError:
    print('⚠️  Numba not installed (optional)')
except Exception as e:
    print(f'❌ Compatibility issue: {e}')
"

echo ""
echo "✅ Fix complete! Restart your dev server for changes to take effect."
