"""
Stage Buddy V2 - Audio Backend Initialization

This module MUST be imported before any SpeechBrain or torchaudio usage.
It properly detects and configures a working audio backend, or raises
a clear error if none is available.

NO FALLBACKS - either we have a verified working backend, or we fail fast.
"""

import os
import logging
import tempfile
import warnings

logger = logging.getLogger(__name__)

# Track initialization state
_BACKEND_INITIALIZED = False
_WORKING_BACKEND = None


class AudioBackendError(Exception):
    """Raised when no working audio backend can be found."""
    pass


def _test_soundfile_backend() -> bool:
    """Test that soundfile can actually read/write audio."""
    try:
        import soundfile as sf
        import numpy as np

        # Create a small test signal
        sample_rate = 16000
        duration = 0.1  # 100ms
        samples = int(sample_rate * duration)
        test_signal = np.zeros(samples, dtype=np.float32)

        # Write to temp file and read back
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as f:
            sf.write(f.name, test_signal, sample_rate)
            data, sr = sf.read(f.name)

            if sr != sample_rate or len(data) != samples:
                logger.warning("soundfile read/write test produced unexpected results")
                return False

        logger.info("soundfile backend verified working")
        return True

    except Exception as e:
        logger.debug(f"soundfile backend test failed: {e}")
        return False


def _test_scipy_backend() -> bool:
    """Test that scipy.io.wavfile can read/write audio."""
    try:
        from scipy.io import wavfile
        import numpy as np

        sample_rate = 16000
        duration = 0.1
        samples = int(sample_rate * duration)
        test_signal = np.zeros(samples, dtype=np.int16)

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as f:
            wavfile.write(f.name, sample_rate, test_signal)
            sr, data = wavfile.read(f.name)

            if sr != sample_rate or len(data) != samples:
                logger.warning("scipy backend read/write test produced unexpected results")
                return False

        logger.info("scipy backend verified working")
        return True

    except Exception as e:
        logger.debug(f"scipy backend test failed: {e}")
        return False


def _configure_torchaudio_shim():
    """
    Add compatibility shim for torchaudio.list_audio_backends if missing.

    This must be called before importing SpeechBrain, as SpeechBrain
    internally calls this function which was removed in torchaudio 2.1+.
    """
    try:
        import torchaudio
    except ImportError:
        # torchaudio not installed - will be handled elsewhere
        return

    if hasattr(torchaudio, 'list_audio_backends'):
        # Already exists, nothing to do
        return

    # Create shim that returns verified working backends
    def _list_audio_backends():
        """Compatibility shim returning only verified working backends."""
        backends = []

        # Only include backends we've actually tested
        if _WORKING_BACKEND == 'soundfile':
            backends.append('soundfile')
        elif _WORKING_BACKEND == 'scipy':
            backends.append('scipy')

        # If we have a working backend, return it
        if backends:
            return backends

        # Fall back to attempting soundfile (most common)
        try:
            import soundfile
            backends.append('soundfile')
        except ImportError:
            pass

        return backends if backends else ['soundfile']

    torchaudio.list_audio_backends = _list_audio_backends
    logger.debug("Installed torchaudio.list_audio_backends compatibility shim")


def _configure_torchaudio_backend():
    """Configure torchaudio to use the verified working backend."""
    try:
        import torchaudio
    except ImportError:
        return

    if not hasattr(torchaudio, 'set_audio_backend'):
        # Newer torchaudio versions handle this automatically
        return

    if _WORKING_BACKEND == 'soundfile':
        try:
            torchaudio.set_audio_backend('soundfile')
            logger.debug("Configured torchaudio to use soundfile backend")
        except Exception:
            # Backend selection may be automatic in newer versions
            pass


def initialize_audio_backend(require_backend: bool = True) -> str | None:
    """
    Initialize and verify a working audio backend.

    This must be called before importing SpeechBrain or using torchaudio
    for audio loading.

    Args:
        require_backend: If True, raises AudioBackendError if no backend works.
                        If False, returns None when no backend is available.

    Returns:
        Name of the working backend ('soundfile', 'scipy', etc.) or None.

    Raises:
        AudioBackendError: If require_backend=True and no backend works.
    """
    global _BACKEND_INITIALIZED, _WORKING_BACKEND

    if _BACKEND_INITIALIZED:
        if require_backend and _WORKING_BACKEND is None:
            raise AudioBackendError(
                "No working audio backend available. "
                "Install soundfile: pip install soundfile"
            )
        return _WORKING_BACKEND

    logger.info("Initializing audio backend...")

    # Test backends in priority order
    backends_to_test = [
        ('soundfile', _test_soundfile_backend),
        ('scipy', _test_scipy_backend),
    ]

    for name, test_fn in backends_to_test:
        if test_fn():
            _WORKING_BACKEND = name
            logger.info(f"Using audio backend: {name}")
            break

    _BACKEND_INITIALIZED = True

    if _WORKING_BACKEND is None:
        error_msg = (
            "No working audio backend found. SpeechBrain requires a working "
            "audio backend to load and process audio files.\n\n"
            "Install soundfile (recommended):\n"
            "    pip install soundfile\n\n"
            "Or install scipy:\n"
            "    pip install scipy\n"
        )

        if require_backend:
            raise AudioBackendError(error_msg)
        else:
            logger.error(error_msg)
            return None

    # Configure torchaudio with the working backend
    _configure_torchaudio_shim()
    _configure_torchaudio_backend()

    return _WORKING_BACKEND


def get_working_backend() -> str | None:
    """
    Get the name of the currently configured working backend.

    Returns None if initialize_audio_backend() hasn't been called yet
    or if no backend is available.
    """
    return _WORKING_BACKEND


def ensure_backend_available():
    """
    Ensure a working audio backend is available.

    Raises AudioBackendError if no backend is available.
    Call this before any audio processing operations.
    """
    if not _BACKEND_INITIALIZED:
        initialize_audio_backend(require_backend=True)
    elif _WORKING_BACKEND is None:
        raise AudioBackendError(
            "No working audio backend available. "
            "Install soundfile: pip install soundfile"
        )


# Auto-initialize on import with require_backend=False
# This allows the module to be imported without immediate failure,
# but will set up the backend properly if one is available.
try:
    # Suppress warnings during initialization
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        initialize_audio_backend(require_backend=False)
except Exception as e:
    logger.warning(f"Audio backend auto-initialization failed: {e}")
