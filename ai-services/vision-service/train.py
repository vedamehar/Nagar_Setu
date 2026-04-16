"""Training entrypoint for Smart Civic Road Issue Detection.

Trains YOLOv8 on two classes:
- 0: pothole
- 1: damaged_road
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict

from ultralytics import YOLO

try:
    import torch
except Exception:  # pragma: no cover - import guard for minimal environments
    torch = None

if torch is not None:
    # Windows can hit shared file mapping limits with multiprocessing dataloaders.
    try:
        torch.multiprocessing.set_sharing_strategy("file_system")
    except Exception:
        pass


def setup_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLOv8 for road issue detection")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Pretrained model")
    parser.add_argument("--data", type=str, default="data.yaml", help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (recommend fixed value on Windows)")
    parser.add_argument("--project", type=str, default="runs", help="Run output root")
    parser.add_argument("--name", type=str, default="train", help="Run name")
    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help="Device: 0, 0,1, cuda, cuda:0, auto (GPU-only by default)",
    )
    parser.add_argument(
        "--allow-cpu",
        action="store_true",
        help="Allow CPU fallback when CUDA is unavailable (disabled by default)",
    )
    parser.add_argument("--workers", type=int, default=0, help="Dataloader workers (0 is safest on Windows)")
    parser.add_argument(
        "--enable-pin-memory",
        action="store_true",
        help="Enable dataloader pin_memory (off by default for Windows CUDA stability)",
    )
    parser.add_argument(
        "--cache",
        type=str,
        default="False",
        choices=["False", "ram", "disk"],
        help="Dataset cache mode: False, ram, or disk",
    )
    parser.add_argument(
        "--amp",
        action="store_true",
        help="Enable AMP mixed precision (disabled by default for maximum compatibility)",
    )
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    return parser.parse_args()


def resolve_device(device_arg: str, allow_cpu: bool) -> str:
    device = (device_arg or "auto").strip().lower()

    if device == "auto":
        if torch is not None and torch.cuda.is_available() and torch.cuda.device_count() > 0:
            logging.info("Auto device selected: cuda:0 (%s)", torch.cuda.get_device_name(0))
            return "0"
        if allow_cpu:
            logging.info("Auto device selected: cpu")
            return "cpu"
        raise RuntimeError(
            "CUDA is unavailable and --allow-cpu was not set. "
            "Install CUDA-enabled PyTorch or pass --allow-cpu explicitly."
        )

    if device.startswith("cuda"):
        if torch is None or not torch.cuda.is_available() or torch.cuda.device_count() == 0:
            raise RuntimeError(
                "CUDA device requested but no CUDA-enabled PyTorch device is available. "
                "Install CUDA PyTorch build and verify with torch.cuda.is_available()."
            )
        if device == "cuda":
            return "0"
        return device.replace("cuda:", "")

    if device.isdigit() or "," in device or device == "cpu":
        if device == "cpu" and not allow_cpu:
            raise RuntimeError("CPU device is blocked by default. Use --allow-cpu to enable it.")
        return device

    raise ValueError("Invalid --device value. Use one of: auto, cpu, 0, 0,1, cuda, cuda:0")


def log_runtime_device_info(selected_device: str) -> None:
    if torch is None:
        logging.info("PyTorch import unavailable; proceeding with Ultralytics defaults.")
        return

    logging.info("PyTorch: %s", torch.__version__)
    logging.info("CUDA available: %s", torch.cuda.is_available())
    logging.info("CUDA device count: %s", torch.cuda.device_count())
    if torch.cuda.is_available() and torch.cuda.device_count() > 0:
        for idx in range(torch.cuda.device_count()):
            logging.info("GPU %d: %s", idx, torch.cuda.get_device_name(idx))
    logging.info("Training device argument: %s", selected_device)


def to_plain_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "results_dict"):
        return obj.results_dict
    if isinstance(obj, dict):
        return obj
    return {"value": str(obj)}


def patch_ultralytics_dataloader(disable_pin_memory: bool) -> None:
    """Patch Ultralytics dataloader calls to avoid Windows CUDA mapping failures."""
    if not disable_pin_memory:
        return

    try:
        from ultralytics.data import build as data_build
        from ultralytics.models.yolo.detect import train as detect_train
        from ultralytics.models.yolo.detect import val as detect_val
    except Exception as exc:
        logging.warning("Could not patch dataloader pin_memory behavior: %s", exc)
        return

    base = data_build.build_dataloader
    if getattr(base, "_pvg_pin_memory_patched", False):
        return

    def _build_dataloader_patched(*args: Any, **kwargs: Any):
        kwargs["pin_memory"] = False
        return base(*args, **kwargs)

    setattr(_build_dataloader_patched, "_pvg_pin_memory_patched", True)

    data_build.build_dataloader = _build_dataloader_patched
    detect_train.build_dataloader = _build_dataloader_patched
    detect_val.build_dataloader = _build_dataloader_patched
    logging.info("Forced Ultralytics dataloaders to pin_memory=False")


def main() -> None:
    setup_logger()
    args = parse_args()
    selected_device = resolve_device(args.device, args.allow_cpu)
    log_runtime_device_info(selected_device)
    patch_ultralytics_dataloader(disable_pin_memory=not args.enable_pin_memory)

    Path(args.project).mkdir(parents=True, exist_ok=True)

    # Keep CUDA allocator behavior stable for long runs.
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    logging.info("Loading model: %s", args.model)
    model = YOLO(args.model)

    cache_value: str | bool = False if args.cache == "False" else args.cache

    train_kwargs: Dict[str, Any] = {
        "data": args.data,
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": args.project,
        "name": args.name,
        "device": selected_device,
        "workers": args.workers,
        "patience": args.patience,
        "cache": cache_value,
        "amp": args.amp,
    }

    logging.info(
        "Starting training with settings: batch=%s workers=%s pin_memory=%s cache=%s amp=%s",
        train_kwargs["batch"],
        train_kwargs["workers"],
        args.enable_pin_memory,
        train_kwargs["cache"],
        train_kwargs["amp"],
    )

    try:
        train_results = model.train(**train_kwargs)
    except Exception as exc:
        message = str(exc).lower()
        retryable = (
            "couldn't open shared file mapping" in message
            or "resource already mapped" in message
            or "acceleratorerror" in message
        )
        if not retryable:
            raise

        logging.warning("Encountered dataloader/CUDA mapping error: %s", exc)
        logging.warning("Retrying once with ultra-safe settings for Windows GPU training")

        safe_kwargs = dict(train_kwargs)
        patch_ultralytics_dataloader(disable_pin_memory=True)
        safe_kwargs.update({"workers": 0, "cache": False, "batch": 8, "amp": False})
        train_results = model.train(**safe_kwargs)

    logging.info("Training complete. Running validation on best checkpoint")
    save_dir = None
    if hasattr(model, "trainer") and getattr(model.trainer, "save_dir", None):
        save_dir = Path(model.trainer.save_dir)
    if save_dir is None:
        save_dir = Path(args.project) / "detect" / args.name

    best_path = save_dir / "weights" / "best.pt"
    if not best_path.exists():
        raise FileNotFoundError(f"best.pt not found at {best_path}")

    best_model = YOLO(str(best_path))
    val_results = best_model.val(data=args.data)

    summary = {
        "best_model": str(best_path),
        "train": to_plain_dict(train_results),
        "val": to_plain_dict(val_results),
    }

    summary_path = save_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Keep a stable output path for downstream inference commands.
    canonical_weights_dir = Path("runs") / "detect" / "train" / "weights"
    canonical_weights_dir.mkdir(parents=True, exist_ok=True)
    canonical_best = canonical_weights_dir / "best.pt"
    canonical_last = canonical_weights_dir / "last.pt"
    shutil.copy2(best_path, canonical_best)
    last_path = save_dir / "weights" / "last.pt"
    if last_path.exists():
        shutil.copy2(last_path, canonical_last)

    logging.info("Best checkpoint: %s", best_path)
    logging.info("Canonical best checkpoint copy: %s", canonical_best)
    logging.info("Training summary saved to: %s", summary_path)


if __name__ == "__main__":
    main()
