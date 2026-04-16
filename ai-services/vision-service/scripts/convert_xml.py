"""Convert Pascal VOC XML annotations from RDD2022 India to YOLO labels.

Class mapping:
- D40 -> pothole (0)
- D00, D10, D20 -> damaged_road (1)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import etree
from tqdm import tqdm

CLASS_MAP: Dict[str, int] = {
    "D40": 0,
    "D00": 1,
    "D10": 1,
    "D20": 1,
}


def setup_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def parse_int(node: Optional[etree._Element], default: int = 0) -> int:
    if node is None or node.text is None:
        return default
    try:
        return int(float(node.text.strip()))
    except ValueError:
        return default


def to_yolo_bbox(
    width: int,
    height: int,
    xmin: int,
    ymin: int,
    xmax: int,
    ymax: int,
) -> Optional[Tuple[float, float, float, float]]:
    if width <= 0 or height <= 0:
        return None

    xmin = max(0, min(xmin, width - 1))
    ymin = max(0, min(ymin, height - 1))
    xmax = max(0, min(xmax, width - 1))
    ymax = max(0, min(ymax, height - 1))

    if xmax <= xmin or ymax <= ymin:
        return None

    bw = xmax - xmin
    bh = ymax - ymin
    xc = xmin + bw / 2.0
    yc = ymin + bh / 2.0

    return xc / width, yc / height, bw / width, bh / height


def convert_single_xml(xml_path: Path, output_dir: Path) -> Tuple[int, int]:
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    size = root.find("size")
    width = parse_int(size.find("width") if size is not None else None)
    height = parse_int(size.find("height") if size is not None else None)

    yolo_lines: List[str] = []
    total_objects = 0

    for obj in root.findall("object"):
        name = obj.findtext("name", default="").strip()
        if name not in CLASS_MAP:
            continue

        bbox = obj.find("bndbox")
        if bbox is None:
            continue

        xmin = parse_int(bbox.find("xmin"))
        ymin = parse_int(bbox.find("ymin"))
        xmax = parse_int(bbox.find("xmax"))
        ymax = parse_int(bbox.find("ymax"))

        yolo_bbox = to_yolo_bbox(width, height, xmin, ymin, xmax, ymax)
        if yolo_bbox is None:
            continue

        class_id = CLASS_MAP[name]
        x_center, y_center, w, h = yolo_bbox
        yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")
        total_objects += 1

    output_dir.mkdir(parents=True, exist_ok=True)
    label_path = output_dir / f"{xml_path.stem}.txt"
    label_path.write_text("\n".join(yolo_lines), encoding="utf-8")

    return total_objects, len(yolo_lines)


def convert_all(xml_dir: Path, output_dir: Path) -> None:
    xml_files = sorted(xml_dir.glob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(f"No XML files found in: {xml_dir}")

    kept = 0
    written = 0

    for xml_file in tqdm(xml_files, desc="Converting XML -> YOLO"):
        total_objects, kept_objects = convert_single_xml(xml_file, output_dir)
        written += total_objects
        kept += kept_objects

    logging.info("Converted %d XML files", len(xml_files))
    logging.info("Kept objects after class mapping: %d", kept)
    logging.info("Processed objects from mapped classes: %d", written)


def parse_args() -> argparse.Namespace:
    default_xml = Path(r"D:\Work\Hack\PVG - App\Dataset\RDD2022_India\India\train\annotations\xmls")
    default_out = Path("data/raw/annotations")

    parser = argparse.ArgumentParser(description="Convert Pascal VOC XML files to YOLO txt labels")
    parser.add_argument("--xml-dir", type=Path, default=default_xml, help="Folder containing XML files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_out,
        help="Folder to write YOLO .txt labels",
    )
    return parser.parse_args()


def main() -> None:
    setup_logger()
    args = parse_args()

    logging.info("XML source: %s", args.xml_dir)
    logging.info("YOLO labels output: %s", args.output_dir)

    convert_all(args.xml_dir, args.output_dir)


if __name__ == "__main__":
    main()
