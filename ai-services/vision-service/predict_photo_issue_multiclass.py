import argparse
import json
from pathlib import Path
from typing import Dict

import torch
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict issue and severity from one image using multiclass classifier."
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument(
        "--model",
        type=str,
        default="runs/classify/train_multiclass/weights/best.pt",
        help="Path to trained classification model.",
    )
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--output-json", type=Path, default=Path("runs/classify/single_prediction_multiclass.json"))
    return parser.parse_args()


def resolve_device(device_arg: str, allow_cpu: bool) -> str:
    cuda_ok = torch.cuda.is_available()
    if device_arg == "auto":
        if cuda_ok:
            return "0"
        if allow_cpu:
            return "cpu"
        raise RuntimeError("CUDA is not available. Use --allow-cpu to run on CPU.")

    if device_arg == "cpu":
        if allow_cpu:
            return "cpu"
        raise RuntimeError("CPU fallback is disabled. Use --allow-cpu to enable it.")

    if not cuda_ok and not allow_cpu:
        raise RuntimeError("GPU requested but CUDA is unavailable. Use --allow-cpu to proceed on CPU.")

    return device_arg if cuda_ok else "cpu"


def map_issue(class_name: str) -> str:
    class_key = class_name.strip().lower()
    if class_key == "pothole":
        return "pothole"
    if class_key == "patch":
        return "damaged_road"
    return "no_road_issue"


def confidence_to_severity(issue: str, conf: float) -> str:
    if issue == "no_road_issue":
        return "NONE"

    if conf >= 0.85:
        return "HIGH"
    if conf >= 0.6:
        return "MEDIUM"
    return "LOW"


def severity_to_priority(issue: str, severity: str) -> str:
    if issue == "no_road_issue":
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


def predict(image_path: Path, model_path: str, device: str) -> Dict:
    model = YOLO(model_path)
    result = model.predict(source=str(image_path), device=device, verbose=False)[0]

    top1_idx = int(result.probs.top1)
    top1_conf = float(result.probs.top1conf)
    class_name = result.names[top1_idx]

    issue = map_issue(class_name)
    severity = confidence_to_severity(issue, top1_conf)
    priority = severity_to_priority(issue, severity)

    return {
        "image": str(image_path),
        "predicted_class": class_name,
        "class_confidence": round(top1_conf, 4),
        "issue": issue,
        "severity": severity,
        "priority": priority,
        "note": (
            "This dataset is image classification format, so count/multiple pothole localization "
            "is not available from this model."
        ),
    }


def main() -> None:
    args = parse_args()
    if not args.image.exists():
        raise FileNotFoundError(f"Image not found: {args.image}")

    device = resolve_device(args.device, args.allow_cpu)
    output = predict(args.image, args.model, device)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(json.dumps(output, indent=2))
    print(f"Saved output JSON: {args.output_json}")


if __name__ == "__main__":
    main()
