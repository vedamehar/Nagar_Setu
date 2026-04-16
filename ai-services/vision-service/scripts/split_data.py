"""Split images and YOLO labels into train/val folders.

This script preserves image-label mapping by filename stem.
"""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path
from typing import List, Sequence, Tuple

from sklearn.model_selection import train_test_split
from tqdm import tqdm

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def setup_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def list_images(image_dir: Path) -> List[Path]:
    images: List[Path] = []
    for p in image_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            images.append(p)
    return sorted(images)


def copy_pairs(
    images: Sequence[Path],
    source_labels: Path,
    out_images: Path,
    out_labels: Path,
) -> Tuple[int, int]:
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    copied = 0
    created_empty = 0

    for img_path in tqdm(images, desc=f"Copying -> {out_images.name}"):
        dst_img = out_images / img_path.name
        shutil.copy2(img_path, dst_img)

        src_label = source_labels / f"{img_path.stem}.txt"
        dst_label = out_labels / src_label.name

        if src_label.exists():
            shutil.copy2(src_label, dst_label)
        else:
            dst_label.write_text("", encoding="utf-8")
            created_empty += 1

        copied += 1

    return copied, created_empty


def parse_args() -> argparse.Namespace:
    default_images = Path(r"D:\Work\Hack\PVG - App\Dataset\RDD2022_India\India\train\images")

    parser = argparse.ArgumentParser(description="Split YOLO dataset into train and validation")
    parser.add_argument("--source-images", type=Path, default=default_images, help="Source train images")
    parser.add_argument(
        "--source-labels",
        type=Path,
        default=Path("data/raw/annotations"),
        help="YOLO labels generated from XML conversion",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/dataset"),
        help="Output dataset root",
    )
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Validation split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def main() -> None:
    setup_logger()
    args = parse_args()

    if not args.source_images.exists():
        raise FileNotFoundError(f"Source image folder not found: {args.source_images}")
    if not args.source_labels.exists():
        raise FileNotFoundError(f"Source label folder not found: {args.source_labels}")

    images = list_images(args.source_images)
    if not images:
        raise RuntimeError(f"No images found in: {args.source_images}")

    train_imgs, val_imgs = train_test_split(
        images,
        test_size=args.val_ratio,
        random_state=args.seed,
        shuffle=True,
    )

    train_img_dir = args.output_root / "images" / "train"
    val_img_dir = args.output_root / "images" / "val"
    train_lbl_dir = args.output_root / "labels" / "train"
    val_lbl_dir = args.output_root / "labels" / "val"

    train_count, train_empty = copy_pairs(
        train_imgs,
        args.source_labels,
        train_img_dir,
        train_lbl_dir,
    )
    val_count, val_empty = copy_pairs(
        val_imgs, args.source_labels, val_img_dir, val_lbl_dir
    )

    logging.info("Total images: %d", len(images))
    logging.info("Train images: %d", train_count)
    logging.info("Val images: %d", val_count)
    logging.info("Empty labels created (train): %d", train_empty)
    logging.info("Empty labels created (val): %d", val_empty)


if __name__ == "__main__":
    main()
