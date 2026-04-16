import argparse
import json
from pathlib import Path
from typing import List

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate multiclass pothole classifier on test split.")
    parser.add_argument("--model", type=str, required=True, help="Path to trained classification checkpoint.")
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=Path("data/pothole_multiclass_cls/test"),
        help="Path to class-folder-based test split.",
    )
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--output-json", type=Path, default=Path("runs/classify/eval_multiclass.json"))
    return parser.parse_args()


def collect_test_samples(test_dir: Path) -> tuple[List[Path], List[str], List[str]]:
    class_names = sorted([d.name for d in test_dir.iterdir() if d.is_dir()])
    image_paths: List[Path] = []
    labels: List[str] = []

    for cls in class_names:
        cls_dir = test_dir / cls
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"):
            for img in cls_dir.glob(ext):
                image_paths.append(img)
                labels.append(cls)

    if not image_paths:
        raise RuntimeError(f"No test images found under {test_dir}")

    return image_paths, labels, class_names


def main() -> None:
    args = parse_args()

    model = YOLO(args.model)
    image_paths, y_true, classes = collect_test_samples(args.test_dir)

    preds = model.predict(
        source=[str(p) for p in image_paths],
        device=args.device,
        verbose=False,
    )

    y_pred = [classes[int(r.probs.top1)] for r in preds]

    acc = accuracy_score(y_true, y_pred)
    f1w = f1_score(y_true, y_pred, average="weighted")
    f1m = f1_score(y_true, y_pred, average="macro")
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    report = classification_report(y_true, y_pred, labels=classes, output_dict=True, zero_division=0)

    output = {
        "model": args.model,
        "test_dir": str(args.test_dir),
        "num_samples": len(y_true),
        "accuracy": round(float(acc), 4),
        "f1_weighted": round(float(f1w), 4),
        "f1_macro": round(float(f1m), 4),
        "classes": classes,
        "confusion_matrix": np.asarray(cm).tolist(),
        "classification_report": report,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(json.dumps(output, indent=2))
    print(f"Saved evaluation JSON: {args.output_json}")


if __name__ == "__main__":
    main()
