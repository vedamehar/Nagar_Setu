"""Single-photo civic road issue prediction CLI.

Upload one image path, run YOLO detection, and return issue + severity + priority JSON.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from ultralytics import YOLO

from infer import process, resolve_device


def predict_uploaded_photo(
    image_path: str,
    model_path: str,
    device: str = "0",
    allow_cpu: bool = False,
    conf: float = 0.25,
    iou: float = 0.45,
    save_annotated: bool = True,
    annotated_dir: str = "runs/infer/single",
) -> Dict[str, Any]:
    """Predict issue details for a single uploaded photo."""
    selected_device = resolve_device(device, allow_cpu)
    model = YOLO(model_path)

    return process(
        image_path=image_path,
        model=model,
        device=selected_device,
        conf=conf,
        iou=iou,
        save_annotated=save_annotated,
        annotated_dir=annotated_dir,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict road issue and severity from one uploaded image"
    )
    parser.add_argument(
        "--image",
        type=str,
        required=True,
        help="Path to uploaded image (jpg/jpeg/png/bmp/webp)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="runs/detect/runs/train2/weights/best.pt",
        help="Path to trained YOLO weights",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help="Device: 0, cuda:0, auto (GPU-only by default)",
    )
    parser.add_argument(
        "--allow-cpu",
        action="store_true",
        help="Allow CPU fallback when CUDA is unavailable",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold")
    parser.add_argument(
        "--save-annotated",
        action="store_true",
        help="Save image with drawn bounding boxes",
    )
    parser.add_argument(
        "--annotated-dir",
        type=str,
        default="runs/infer/single",
        help="Folder to save annotated image",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="runs/infer/single_prediction.json",
        help="Path to save single prediction JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    image_path = Path(args.image)
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    result = predict_uploaded_photo(
        image_path=str(image_path),
        model_path=args.model,
        device=args.device,
        allow_cpu=args.allow_cpu,
        conf=args.conf,
        iou=args.iou,
        save_annotated=args.save_annotated,
        annotated_dir=args.annotated_dir,
    )

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("Prediction result:")
    print(json.dumps(result, indent=2))
    print(f"Saved JSON to: {out_path}")


if __name__ == "__main__":
    main()
