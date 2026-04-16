import argparse
import csv
import shutil
from pathlib import Path
from typing import Dict, List


SPLIT_MAP = {
    "train": "train",
    "valid": "val",
    "test": "test",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Roboflow multiclass CSV dataset into YOLO classify folder layout."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Path to the Roboflow dataset root (contains train/valid/test).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/pothole_multiclass_cls"),
        help="Output folder for YOLO classification dataset.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of creating hard links.",
    )
    return parser.parse_args()


def read_classes_csv(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise ValueError(f"No rows found in {csv_path}")
    return rows


def get_one_hot_label(row: Dict[str, str], class_names: List[str]) -> str:
    positives = [name for name in class_names if str(row.get(name, "0")).strip() == "1"]
    if len(positives) != 1:
        raise ValueError(
            f"Expected exactly one positive class for {row.get('filename')}, got: {positives}"
        )
    return positives[0]


def link_or_copy(src: Path, dst: Path, copy_mode: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    if copy_mode:
        shutil.copy2(src, dst)
        return
    try:
        dst.hardlink_to(src)
    except OSError:
        shutil.copy2(src, dst)


def prepare_split(
    source_split_dir: Path,
    dest_split_dir: Path,
    class_names: List[str],
    copy_mode: bool,
) -> Dict[str, int]:
    classes_csv = source_split_dir / "_classes.csv"
    rows = read_classes_csv(classes_csv)

    counts = {name: 0 for name in class_names}

    # Ensure every split has all class folders so class count remains consistent.
    for cls_name in class_names:
        (dest_split_dir / cls_name).mkdir(parents=True, exist_ok=True)

    for row in rows:
        file_name = row["filename"]
        label = get_one_hot_label(row, class_names)
        src_image = source_split_dir / file_name
        if not src_image.exists():
            raise FileNotFoundError(f"Image missing: {src_image}")

        dst_image = dest_split_dir / label / file_name
        link_or_copy(src_image, dst_image, copy_mode=copy_mode)
        counts[label] += 1

    return counts


def main() -> None:
    args = parse_args()

    source_root = args.source_root
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Source: {source_root}")
    print(f"Output: {output_root}")

    # Use train header as the source-of-truth class order for all splits.
    train_rows = read_classes_csv(source_root / "train" / "_classes.csv")
    class_names = [c for c in train_rows[0].keys() if c != "filename"]

    overall = {}
    for src_name, dst_name in SPLIT_MAP.items():
        src_split = source_root / src_name
        if not src_split.exists():
            raise FileNotFoundError(f"Missing split folder: {src_split}")

        dst_split = output_root / dst_name
        counts = prepare_split(src_split, dst_split, class_names=class_names, copy_mode=args.copy)
        overall[dst_name] = counts
        print(f"Prepared split: {dst_name} -> {counts}")

    print("Dataset preparation complete.")


if __name__ == "__main__":
    main()
