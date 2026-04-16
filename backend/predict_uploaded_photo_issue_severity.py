import argparse
import json
from pathlib import Path
from typing import Dict, List

import torch
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict road issue and severity from one uploaded photo (multiclass classifier)."
    )
    parser.add_argument("--image", type=Path, required=True, help="Path to uploaded image.")
    parser.add_argument(
        "--model",
        type=str,
        default="auto",
        help=(
            "Path to trained model weights. Use 'auto' to search common locations "
            "(recommended)."
        ),
    )
    parser.add_argument("--device", type=str, default="auto", help="auto, 0, 1, ... or cpu")
    parser.add_argument("--allow-cpu", action="store_true", help="Allow CPU fallback if CUDA is unavailable.")
    parser.add_argument(
        "--medium-threshold",
        type=float,
        default=0.60,
        help="Confidence threshold for MEDIUM severity.",
    )
    parser.add_argument(
        "--high-threshold",
        type=float,
        default=0.85,
        help="Confidence threshold for HIGH severity.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("runs/classify/uploaded_photo_prediction.json"),
        help="Where to save prediction JSON.",
    )
    return parser.parse_args()


def resolve_device(device_arg: str, allow_cpu: bool) -> str:
    cuda_ok = torch.cuda.is_available()

    if device_arg == "auto":
        if cuda_ok:
            return "0"
        if allow_cpu:
            return "cpu"
        raise RuntimeError("CUDA is not available. Re-run with --allow-cpu to use CPU.")

    if device_arg == "cpu":
        if allow_cpu:
            return "cpu"
        raise RuntimeError("CPU fallback disabled. Pass --allow-cpu to enable CPU mode.")

    if not cuda_ok:
        if allow_cpu:
            return "cpu"
        raise RuntimeError("GPU requested but CUDA is unavailable. Use --allow-cpu or fix CUDA.")

    return device_arg


def find_model_weights(model_arg: str) -> Path:
    if model_arg != "auto":
        p = Path(model_arg)
        if not p.exists():
            raise FileNotFoundError(f"Model not found: {p}")
        return p

    script_dir = Path(__file__).resolve().parent
    candidates: List[Path] = [
        Path("runs/classify/train_multiclass/weights/best.pt"),
        script_dir / "runs/classify/train_multiclass/weights/best.pt",
        Path("runs/classify/runs/train_multiclass/weights/best.pt"),
        script_dir / "runs/classify/runs/train_multiclass/weights/best.pt",
    ]

    for c in candidates:
        if c.exists():
            return c

    searched = "\n".join(str(c) for c in candidates)
    raise FileNotFoundError(
        "Could not find trained multiclass model automatically. "
        "Pass --model <path-to-best.pt>. Searched:\n"
        f"{searched}"
    )


def map_issue(class_name: str) -> str:
    key = class_name.strip().lower()
    if key == "pothole":
        return "pothole"
    if key == "patch":
        return "damaged_road"
    return "no_road_issue"


def confidence_to_severity(issue: str, confidence: float, medium_thr: float, high_thr: float) -> str:
    if issue == "no_road_issue":
        return "NONE"

    if confidence >= high_thr:
        return "HIGH"
    if confidence >= medium_thr:
        return "MEDIUM"
    return "LOW"


def severity_to_priority(issue: str, severity: str) -> str:
    if issue == "no_road_issue" or severity == "NONE":
        return "LOW"

    score = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}[severity]
    if issue == "pothole":
        score += 1

    if score >= 4:
        return "CRITICAL"
    if score == 3:
        return "HIGH"
    if score == 2:
        return "MEDIUM"
    return "LOW"


def predict_one(
    image_path: Path,
    model_path: Path,
    device: str,
    medium_thr: float,
    high_thr: float,
) -> Dict:
    model = YOLO(str(model_path))
    result = model.predict(source=str(image_path), device=device, verbose=False)[0]

    top1_idx = int(result.probs.top1)
    top1_conf = float(result.probs.top1conf)
    class_name = result.names[top1_idx]

    issue = map_issue(class_name)
    severity = confidence_to_severity(issue, top1_conf, medium_thr, high_thr)
    priority = severity_to_priority(issue, severity)

    return {
        "image": str(image_path),
        "model": str(model_path),
        "predicted_class": class_name,
        "class_confidence": round(top1_conf, 4),
        "issue": issue,
        "severity": severity,
        "priority": priority,
        "severity_thresholds": {
            "medium": medium_thr,
            "high": high_thr,
        },
        "note": (
            "This model is image-classification based. It predicts issue type and severity estimate "
            "for the whole image, not bounding-box count of multiple potholes."
        ),
    }


def main() -> None:
    args = parse_args()

    if not args.image.exists():
        raise FileNotFoundError(f"Image not found: {args.image}")

    if args.medium_threshold >= args.high_threshold:
        raise ValueError("--medium-threshold must be lower than --high-threshold")

    model_path = find_model_weights(args.model)
    device = resolve_device(args.device, args.allow_cpu)

    prediction = predict_one(
        image_path=args.image,
        model_path=model_path,
        device=device,
        medium_thr=args.medium_threshold,
        high_thr=args.high_threshold,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(prediction, indent=2), encoding="utf-8")

    print(json.dumps(prediction, indent=2))
    print(f"Saved JSON: {args.output_json}")


if __name__ == "__main__":
    main()
