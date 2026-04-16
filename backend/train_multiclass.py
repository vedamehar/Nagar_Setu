import argparse
import json
import logging
import os
import shutil
from pathlib import Path

import torch
try:
    from ultralytics import YOLO
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency 'ultralytics'. Run with the project venv interpreter:\n"
        "  D:/Work/Hack/PVG - App/Dataset/.venv/Scripts/python.exe train_multiclass.py ...\n"
        "Or install into the active interpreter:\n"
        "  python -m pip install ultralytics"
    ) from exc


LOGGER = logging.getLogger("train_multiclass")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLOv8 classification model on multiclass pothole dataset.")
    parser.add_argument("--model", type=str, default="yolov8n-cls.pt")
    parser.add_argument("--data", type=str, default="data/pothole_multiclass_cls")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--project", type=str, default="runs")
    parser.add_argument("--name", type=str, default="classify/train_multiclass")
    parser.add_argument("--exist-ok", action="store_true")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def resolve_device(device_arg: str, allow_cpu: bool) -> str:
    cuda_ok = torch.cuda.is_available()
    LOGGER.info("PyTorch: %s", torch.__version__)
    LOGGER.info("CUDA available: %s", cuda_ok)
    if cuda_ok:
        LOGGER.info("GPU 0: %s", torch.cuda.get_device_name(0))

    if device_arg == "auto":
        if cuda_ok:
            return "0"
        if allow_cpu:
            return "cpu"
        raise RuntimeError("CUDA not available. Use a CUDA-enabled environment or pass --allow-cpu.")

    if device_arg == "cpu":
        if allow_cpu:
            return "cpu"
        raise RuntimeError("CPU was requested but CPU fallback is disabled. Remove --device cpu or pass --allow-cpu.")

    if not cuda_ok and not allow_cpu:
        raise RuntimeError("GPU device was requested but CUDA is not available.")

    return device_arg if cuda_ok else "cpu"


def copy_canonical_weights(best_path: Path, last_path: Path) -> None:
    canonical = Path("runs/classify/train_multiclass/weights")
    canonical.mkdir(parents=True, exist_ok=True)
    if best_path.exists():
        shutil.copy2(best_path, canonical / "best.pt")
    if last_path.exists():
        shutil.copy2(last_path, canonical / "last.pt")


def main() -> None:
    setup_logging()
    args = parse_args()

    if os.name == "nt":
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    device = resolve_device(args.device, args.allow_cpu)
    LOGGER.info("Training device argument: %s", device)

    model = YOLO(args.model)

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=device,
        project=args.project,
        name=args.name,
        exist_ok=args.exist_ok,
    )

    save_dir = Path(getattr(results, "save_dir", Path(args.project) / args.name))
    weights_dir = save_dir / "weights"
    best_path = weights_dir / "best.pt"
    last_path = weights_dir / "last.pt"

    summary = {
        "save_dir": str(save_dir),
        "best_checkpoint": str(best_path),
        "last_checkpoint": str(last_path),
        "device": device,
    }

    summary_path = save_dir / "summary_multiclass.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    copy_canonical_weights(best_path, last_path)

    LOGGER.info("Training done. Best checkpoint: %s", best_path)
    LOGGER.info("Summary saved: %s", summary_path)


if __name__ == "__main__":
    main()
