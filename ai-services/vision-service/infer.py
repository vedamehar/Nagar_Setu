"""Inference + civic severity and priority engine for road issues."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
from ultralytics import YOLO

try:
    import torch
except Exception:  # pragma: no cover - import guard for minimal environments
    torch = None

CLASS_NAMES = {
    0: "pothole",
    1: "damaged_road",
}

SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH"]


@dataclass
class Detection:
    class_id: int
    label: str
    confidence: float
    bbox: List[float]
    area: float


def severity_score_from_ratio(area_ratio: float) -> int:
    if area_ratio > 0.15:
        return 2
    if area_ratio > 0.05:
        return 1
    return 0


def increase_severity_if_dense(score: int, count: int) -> int:
    if count > 3:
        score += 1
    return min(score, 2)


def compute_severity(total_bbox_area: float, image_area: float, count: int) -> Tuple[str, float]:
    if image_area <= 0:
        return "LOW", 0.0

    ratio = total_bbox_area / image_area
    score = severity_score_from_ratio(ratio)
    score = increase_severity_if_dense(score, count)
    return SEVERITY_ORDER[score], ratio


def infer_issue_type(detections: List[Detection]) -> str:
    if not detections:
        return "none"

    pothole_count = sum(1 for d in detections if d.class_id == 0)
    damaged_count = sum(1 for d in detections if d.class_id == 1)

    if pothole_count >= damaged_count:
        return "pothole"
    return "damaged_road"


def compute_priority(issue_type: str, severity: str, count: int) -> str:
    sev_points = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    score = sev_points.get(severity, 1)

    if issue_type == "pothole":
        score += 1
    if count >= 5:
        score += 2
    elif count >= 3:
        score += 1

    if score >= 6:
        return "CRITICAL"
    if score >= 4:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


def parse_detections(result: Any) -> List[Detection]:
    detections: List[Detection] = []

    boxes = result.boxes
    if boxes is None:
        return detections

    for b in boxes:
        class_id = int(b.cls.item())
        conf = float(b.conf.item())

        x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
        w = max(0.0, x2 - x1)
        h = max(0.0, y2 - y1)
        area = w * h

        detections.append(
            Detection(
                class_id=class_id,
                label=CLASS_NAMES.get(class_id, str(class_id)),
                confidence=conf,
                bbox=[x1, y1, x2, y2],
                area=area,
            )
        )

    return detections


def resolve_device(device_arg: str, allow_cpu: bool) -> str:
    device = (device_arg or "auto").strip().lower()

    if device == "auto":
        if torch is not None and torch.cuda.is_available() and torch.cuda.device_count() > 0:
            return "0"
        if allow_cpu:
            return "cpu"
        raise RuntimeError(
            "CUDA is unavailable and --allow-cpu was not set. "
            "Install CUDA-enabled PyTorch or pass --allow-cpu explicitly."
        )

    if device.startswith("cuda"):
        if torch is None or not torch.cuda.is_available() or torch.cuda.device_count() == 0:
            raise RuntimeError(
                "CUDA device requested but no CUDA-enabled PyTorch device is available."
            )
        if device == "cuda":
            return "0"
        return device.replace("cuda:", "")

    if device.isdigit() or "," in device or device == "cpu":
        if device == "cpu" and not allow_cpu:
            raise RuntimeError("CPU device is blocked by default. Use --allow-cpu to enable it.")
        return device

    raise ValueError("Invalid --device value. Use one of: auto, cpu, 0, 0,1, cuda, cuda:0")


def process(
    image_path: str,
    model: YOLO,
    device: str,
    conf: float = 0.25,
    iou: float = 0.45,
    save_annotated: bool = False,
    annotated_dir: str = "runs/infer",
) -> Dict[str, Any]:
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    h, w = image.shape[:2]
    image_area = float(h * w)

    results = model.predict(
        source=image_path,
        conf=conf,
        iou=iou,
        device=device,
        verbose=False,
    )
    result = results[0]

    detections = parse_detections(result)
    total_bbox_area = sum(d.area for d in detections)
    count = len(detections)

    severity, ratio = compute_severity(total_bbox_area, image_area, count)
    issue_type = infer_issue_type(detections)
    priority = compute_priority(issue_type, severity, count)

    payload: Dict[str, Any] = {
        "image": str(image_path),
        "issue": issue_type,
        "severity": severity,
        "count": count,
        "priority": priority,
        "damage_area_ratio": round(ratio, 6),
        "detections": [
            {
                "class_id": d.class_id,
                "label": d.label,
                "confidence": round(d.confidence, 4),
                "bbox": [round(v, 2) for v in d.bbox],
            }
            for d in detections
        ],
    }

    if save_annotated:
        out_dir = Path(annotated_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plotted = result.plot()
        out_path = out_dir / Path(image_path).name
        cv2.imwrite(str(out_path), plotted)
        payload["annotated_image"] = str(out_path)

    return payload


def run_batch(
    model: YOLO,
    device: str,
    image_dir: Path,
    conf: float,
    iou: float,
    save_annotated: bool,
    annotated_dir: str,
) -> List[Dict[str, Any]]:
    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    images = sorted(
        [p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in valid_exts]
    )

    outputs: List[Dict[str, Any]] = []
    for img in images:
        outputs.append(
            process(
                image_path=str(img),
                model=model,
                device=device,
                conf=conf,
                iou=iou,
                save_annotated=save_annotated,
                annotated_dir=annotated_dir,
            )
        )
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run inference + severity + priority engine")
    parser.add_argument(
        "--model",
        type=str,
        default="runs/detect/train/weights/best.pt",
        help="Path to trained YOLO model",
    )
    parser.add_argument("--image", type=str, default="", help="Path to a single image")
    parser.add_argument(
        "--image-dir",
        type=str,
        default=r"D:\Work\Hack\PVG - App\Dataset\RDD2022_India\India\test\images",
        help="Path to image folder (used when --image is not provided)",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold")
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
    parser.add_argument(
        "--save-annotated",
        action="store_true",
        help="Save images with plotted bounding boxes",
    )
    parser.add_argument(
        "--annotated-dir",
        type=str,
        default="runs/infer",
        help="Folder to save annotated images",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="runs/infer/predictions.json",
        help="JSON file for structured outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_device = resolve_device(args.device, args.allow_cpu)
    model = YOLO(args.model)
    if torch is not None:
        print(f"PyTorch: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        print(f"Using device: {selected_device}")

    if args.image:
        outputs = [
            process(
                image_path=args.image,
                model=model,
                device=selected_device,
                conf=args.conf,
                iou=args.iou,
                save_annotated=args.save_annotated,
                annotated_dir=args.annotated_dir,
            )
        ]
    else:
        outputs = run_batch(
            model=model,
            device=selected_device,
            image_dir=Path(args.image_dir),
            conf=args.conf,
            iou=args.iou,
            save_annotated=args.save_annotated,
            annotated_dir=args.annotated_dir,
        )

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")

    for item in outputs[:5]:
        print(json.dumps(item, indent=2))

    print(f"Saved {len(outputs)} predictions to {out_path}")


if __name__ == "__main__":
    main()
