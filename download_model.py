"""Download the official, versioned MediaPipe model once before local analysis."""
from pathlib import Path
import shutil
import ssl
from urllib.request import urlopen
from zipfile import BadZipFile, ZipFile

import certifi

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/1/pose_landmarker_full.task"
)
MODEL_PATH = Path(__file__).resolve().parent / "models" / "pose_landmarker.task"


def validate_model(path: Path):
    with ZipFile(path) as bundle:
        model_files = [name for name in bundle.namelist() if name.endswith(".tflite")]
        if len(model_files) < 2 or bundle.testzip() is not None:
            raise ValueError("The model bundle is incomplete.")


def main():
    if MODEL_PATH.is_file():
        validate_model(MODEL_PATH)
        print("The local pose model is ready.")
        return

    MODEL_PATH.parent.mkdir(exist_ok=True)
    temporary_path = MODEL_PATH.with_suffix(".part")
    context = ssl.create_default_context(cafile=certifi.where())
    print("Downloading the official pose model...")

    try:
        with urlopen(MODEL_URL, context=context, timeout=120) as response:
            with temporary_path.open("wb") as output:
                shutil.copyfileobj(response, output)

        validate_model(temporary_path)
        temporary_path.replace(MODEL_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)

    print("Saved models/pose_landmarker.task. Camera data is not part of this download.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, BadZipFile):
        raise SystemExit("Model setup failed. Check your internet connection and try again.")
