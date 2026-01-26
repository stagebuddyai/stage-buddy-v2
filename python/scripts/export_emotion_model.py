#!/usr/bin/env python3
"""
Stage Buddy V2 - ONNX Emotion Model Export Script

This script exports the SpeechBrain wav2vec2-based emotion recognition model
to ONNX format, enabling conflict-free inference without triton/numpy issues.

ONE-TIME SETUP: Run this script once to generate the ONNX model.
After export, the main Spirit Engine uses only onnxruntime (zero conflicts).

Usage:
    python scripts/export_emotion_model.py

Requirements:
    This script requires a compatible environment. If you have dependency conflicts,
    it will create a temporary isolated virtualenv automatically.
"""

import os
import sys
import logging
import tempfile
import subprocess
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUT_PATH = MODELS_DIR / "emotion_model.onnx"
METADATA_PATH = MODELS_DIR / "emotion_model_metadata.json"

# Model info
MODEL_SOURCE = "speechbrain/emotion-recognition-wav2vec2-IEMOCAP"
EMOTION_LABELS = ["neu", "hap", "sad", "ang"]  # IEMOCAP labels


def check_direct_export_possible():
    """Check if we can export directly without isolated environment."""
    try:
        import torch
        import numpy as np
        from speechbrain.inference.interfaces import foreign_class

        # Check numpy version compatibility
        np_version = tuple(map(int, np.__version__.split('.')[:2]))
        if np_version >= (2, 4):
            logger.warning(f"NumPy {np.__version__} may cause issues with SpeechBrain export")
            return False

        return True
    except ImportError as e:
        logger.warning(f"Direct export not possible: {e}")
        return False


def create_isolated_environment():
    """Create a temporary isolated virtualenv with compatible dependencies."""
    logger.info("Creating isolated environment for ONNX export...")

    # Create temp directory for venv
    venv_dir = tempfile.mkdtemp(prefix="stagebuddy_onnx_export_")
    venv_python = os.path.join(venv_dir, "bin", "python")

    try:
        # Create virtualenv
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)

        # Upgrade pip
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"],
                      check=True, capture_output=True)

        # Install compatible packages (order matters!)
        packages = [
            "numpy<2.4",  # Compatible with SpeechBrain
            "torch>=2.0.0",
            "torchaudio>=2.0.0",
            "speechbrain>=0.5.0",
            "onnx>=1.14.0",
            "transformers>=4.30.0",
        ]

        logger.info("Installing dependencies in isolated environment...")
        for pkg in packages:
            logger.info(f"  Installing {pkg}...")
            subprocess.run(
                [venv_python, "-m", "pip", "install", pkg],
                check=True,
                capture_output=True
            )

        return venv_dir, venv_python

    except Exception as e:
        # Cleanup on failure
        if os.path.exists(venv_dir):
            shutil.rmtree(venv_dir)
        raise RuntimeError(f"Failed to create isolated environment: {e}")


def export_with_isolated_env(venv_python: str):
    """Run the export in the isolated environment."""
    logger.info("Running ONNX export in isolated environment...")

    export_script = f'''
import os
import sys
import json
import torch
import numpy as np
from pathlib import Path

# Add project to path
sys.path.insert(0, "{PROJECT_ROOT}")

from speechbrain.inference.interfaces import foreign_class

print("Loading SpeechBrain emotion model...")
classifier = foreign_class(
    source="{MODEL_SOURCE}",
    pymodule_file="custom_interface.py",
    classname="CustomEncoderWav2vec2Classifier",
    run_opts={{"device": "cpu"}}
)

print("Model loaded successfully!")

# Get the underlying model components
model = classifier.mods["wav2vec2"]
classifier_head = classifier.mods["avg_pool"]
output_mlp = classifier.mods["output_mlp"]

# Create a wrapper module for export
class EmotionModelWrapper(torch.nn.Module):
    def __init__(self, wav2vec2, avg_pool, output_mlp):
        super().__init__()
        self.wav2vec2 = wav2vec2
        self.avg_pool = avg_pool
        self.output_mlp = output_mlp

    def forward(self, audio):
        # wav2vec2 feature extraction
        features = self.wav2vec2(audio)

        # Average pooling
        pooled = self.avg_pool(features, features)  # SpeechBrain API

        # Classification
        logits = self.output_mlp(pooled)

        # Softmax for probabilities
        probs = torch.nn.functional.softmax(logits, dim=-1)

        return probs

print("Creating wrapper model for ONNX export...")
wrapper = EmotionModelWrapper(model, classifier_head, output_mlp)
wrapper.eval()

# Create dummy input (3 seconds of audio at 16kHz)
dummy_input = torch.randn(1, 48000)

print("Exporting to ONNX format...")
output_path = "{OUTPUT_PATH}"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

torch.onnx.export(
    wrapper,
    dummy_input,
    output_path,
    input_names=["audio"],
    output_names=["emotion_probs"],
    dynamic_axes={{
        "audio": {{0: "batch", 1: "audio_length"}},
        "emotion_probs": {{0: "batch"}}
    }},
    opset_version=14,
    do_constant_folding=True,
)

print(f"ONNX model exported to: {{output_path}}")

# Save metadata
metadata = {{
    "model_source": "{MODEL_SOURCE}",
    "emotion_labels": {EMOTION_LABELS},
    "sample_rate": 16000,
    "input_name": "audio",
    "output_name": "emotion_probs",
    "opset_version": 14
}}

metadata_path = "{METADATA_PATH}"
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)

print(f"Metadata saved to: {{metadata_path}}")
print("Export complete!")
'''

    # Write and run the export script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(export_script)
        export_script_path = f.name

    try:
        result = subprocess.run(
            [venv_python, export_script_path],
            capture_output=True,
            text=True
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode != 0:
            raise RuntimeError(f"Export failed with return code {result.returncode}")

    finally:
        os.unlink(export_script_path)


def export_directly():
    """Export directly in the current environment."""
    import torch
    import json

    logger.info("Loading SpeechBrain emotion model...")

    try:
        from speechbrain.inference.interfaces import foreign_class
    except ImportError:
        from speechbrain.pretrained.interfaces import foreign_class

    classifier = foreign_class(
        source=MODEL_SOURCE,
        pymodule_file="custom_interface.py",
        classname="CustomEncoderWav2vec2Classifier",
        run_opts={"device": "cpu"}
    )

    logger.info("Model loaded! Creating wrapper for ONNX export...")

    # Get model components
    wav2vec2 = classifier.mods["wav2vec2"]
    avg_pool = classifier.mods["avg_pool"]
    output_mlp = classifier.mods["output_mlp"]

    class EmotionModelWrapper(torch.nn.Module):
        def __init__(self, wav2vec2, avg_pool, output_mlp):
            super().__init__()
            self.wav2vec2 = wav2vec2
            self.avg_pool = avg_pool
            self.output_mlp = output_mlp

        def forward(self, audio):
            features = self.wav2vec2(audio)
            pooled = self.avg_pool(features, features)
            logits = self.output_mlp(pooled)
            probs = torch.nn.functional.softmax(logits, dim=-1)
            return probs

    wrapper = EmotionModelWrapper(wav2vec2, avg_pool, output_mlp)
    wrapper.eval()

    # Dummy input
    dummy_input = torch.randn(1, 48000)

    logger.info("Exporting to ONNX...")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        wrapper,
        dummy_input,
        str(OUTPUT_PATH),
        input_names=["audio"],
        output_names=["emotion_probs"],
        dynamic_axes={
            "audio": {0: "batch", 1: "audio_length"},
            "emotion_probs": {0: "batch"}
        },
        opset_version=14,
        do_constant_folding=True,
    )

    logger.info(f"ONNX model saved to: {OUTPUT_PATH}")

    # Save metadata
    metadata = {
        "model_source": MODEL_SOURCE,
        "emotion_labels": EMOTION_LABELS,
        "sample_rate": 16000,
        "input_name": "audio",
        "output_name": "emotion_probs",
        "opset_version": 14
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadata saved to: {METADATA_PATH}")


def verify_onnx_model():
    """Verify the exported ONNX model works."""
    logger.info("Verifying ONNX model...")

    try:
        import onnxruntime as ort
        import numpy as np

        session = ort.InferenceSession(str(OUTPUT_PATH))

        # Test inference
        dummy_audio = np.random.randn(1, 48000).astype(np.float32)
        outputs = session.run(None, {"audio": dummy_audio})

        probs = outputs[0]
        logger.info(f"Test inference successful!")
        logger.info(f"Output shape: {probs.shape}")
        logger.info(f"Output probs: {probs}")
        logger.info(f"Predicted emotion: {EMOTION_LABELS[np.argmax(probs)]}")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


def main():
    """Main export function."""
    logger.info("=" * 60)
    logger.info("Stage Buddy V2 - ONNX Emotion Model Export")
    logger.info("=" * 60)

    # Check if model already exists
    if OUTPUT_PATH.exists():
        logger.info(f"ONNX model already exists at: {OUTPUT_PATH}")
        response = input("Overwrite? [y/N]: ").strip().lower()
        if response != 'y':
            logger.info("Skipping export. Verifying existing model...")
            if verify_onnx_model():
                logger.info("Existing model is valid!")
            return

    # Try direct export first
    if check_direct_export_possible():
        logger.info("Direct export possible, proceeding...")
        try:
            export_directly()
        except Exception as e:
            logger.warning(f"Direct export failed: {e}")
            logger.info("Falling back to isolated environment export...")
            venv_dir, venv_python = create_isolated_environment()
            try:
                export_with_isolated_env(venv_python)
            finally:
                logger.info("Cleaning up isolated environment...")
                shutil.rmtree(venv_dir)
    else:
        logger.info("Creating isolated environment for export...")
        venv_dir, venv_python = create_isolated_environment()
        try:
            export_with_isolated_env(venv_python)
        finally:
            logger.info("Cleaning up isolated environment...")
            shutil.rmtree(venv_dir)

    # Verify
    if OUTPUT_PATH.exists():
        verify_onnx_model()
        logger.info("=" * 60)
        logger.info("Export complete!")
        logger.info(f"Model saved to: {OUTPUT_PATH}")
        logger.info("The Spirit Engine will now automatically use ONNX inference.")
        logger.info("=" * 60)
    else:
        logger.error("Export failed - ONNX model not created")
        sys.exit(1)


if __name__ == "__main__":
    main()
