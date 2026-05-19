from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def write_wav(path: str | Path, audio: np.ndarray, sample_rate_hz: int) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    sf.write(output_path, clipped, sample_rate_hz, subtype="PCM_16")
