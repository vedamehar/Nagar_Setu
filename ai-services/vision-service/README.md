# Smart Civic Road Issue Detection and Prioritization

End-to-end AI pipeline for Smart City civic issue reporting using RDD2022 India.

## 1) What this system does

- Detects road issues in citizen-uploaded images
- Supports two final classes:
  - `0`: pothole
  - `1`: damaged_road (merged from D00/D10/D20)
- Estimates severity from detected damage area
- Assigns civic priority (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- Produces structured JSON for backend integration

## 2) Project structure

```text
project/
├── data/
│   ├── raw/
│   │   ├── images/
│   │   └── annotations/
│   └── dataset/
│       ├── images/
│       │   ├── train/
│       │   └── val/
│       └── labels/
│           ├── train/
│           └── val/
├── scripts/
│   ├── convert_xml.py
│   └── split_data.py
├── runs/
├── infer.py
├── train.py
├── data.yaml
├── requirements.txt
└── README.md
```

## 3) Environment setup

### Windows

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### CUDA / eGPU verification (Windows)

1. Confirm NVIDIA driver detects GPU:

```powershell
nvidia-smi
```

2. Install CUDA-enabled PyTorch (required for GPU training):

```powershell
pip uninstall -y torch torchvision torchaudio
pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio
```

3. Validate CUDA from Python:

```powershell
python -c "import torch; print(torch.__version__); print('cuda', torch.cuda.is_available()); print('count', torch.cuda.device_count()); print([torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])"
```

If `torch.cuda.is_available()` is `False`, training will run on CPU.

### Linux / macOS

```bash
cd /path/to/project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4) Convert XML -> YOLO labels

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
python scripts\convert_xml.py \
  --xml-dir "D:\Work\Hack\PVG - App\Dataset\RDD2022_India\India\train\annotations\xmls" \
  --output-dir "data\raw\annotations"
```

Class mapping used:

- `D40 -> pothole (0)`
- `D00, D10, D20 -> damaged_road (1)`

## 5) Split dataset (train/val)

Uses all images from `India/train/images` and preserves image-label mapping by filename stem.

```powershell
python scripts\split_data.py \
  --source-images "D:\Work\Hack\PVG - App\Dataset\RDD2022_India\India\train\images" \
  --source-labels "data\raw\annotations" \
  --output-root "data\dataset" \
  --val-ratio 0.2 \
  --seed 42
```

## 6) Train YOLOv8n model

```powershell
python train.py --model yolov8n.pt --data data.yaml --epochs 50 --imgsz 640 --batch -1 --device auto
```

Force first GPU explicitly:

```powershell
python train.py --model yolov8n.pt --data data.yaml --epochs 50 --imgsz 640 --batch -1 --device 0
```

Equivalent CLI:

```powershell
yolo detect train model=yolov8n.pt data=data.yaml epochs=50 imgsz=640
```

Best checkpoint path:

```text
runs/detect/train/weights/best.pt
```

## 7) Evaluate model

```powershell
yolo detect val model=runs/detect/train/weights/best.pt data=data.yaml
```

Metrics include mAP, precision, and recall.

## 8) Inference + Severity + Priority

### Single image

```powershell
python infer.py \
  --model runs/detect/train/weights/best.pt \
  --image "D:\path\to\road_image.jpg" \
  --device auto \
  --save-annotated
```

### Test folder batch (RDD2022 India test images)

```powershell
python infer.py \
  --model runs/detect/train/weights/best.pt \
  --image-dir "D:\Work\Hack\PVG - App\Dataset\RDD2022_India\India\test\images" \
  --device auto \
  --save-annotated \
  --output-json runs/infer/predictions.json
```

## 9) Severity rules

- Compute `damage_area_ratio = total_detected_bbox_area / image_area`
- If ratio > `0.15` -> `HIGH`
- Else if ratio > `0.05` -> `MEDIUM`
- Else -> `LOW`
- If detection count > `3`, severity is increased by one level (capped at `HIGH`)

## 10) Priority rules

Inputs:

- dominant issue type (`pothole` or `damaged_road`)
- severity (`LOW`, `MEDIUM`, `HIGH`)
- detection count

Logic:

- Pothole gets extra weight
- Higher count gets extra weight
- Output one of: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

## 11) JSON output schema

Example:

```json
{
  "image": "D:/sample/road.jpg",
  "issue": "pothole",
  "severity": "HIGH",
  "count": 4,
  "priority": "CRITICAL",
  "damage_area_ratio": 0.1734,
  "detections": [
    {
      "class_id": 0,
      "label": "pothole",
      "confidence": 0.9213,
      "bbox": [102.4, 220.8, 280.2, 411.6]
    }
  ]
}
```

## 12) Production notes

- Train for `50-100` epochs as needed
- Prefer GPU (`--device 0`) for faster training
- Verify label quality and class mapping before retraining
- Keep `data.yaml` and class IDs consistent across all scripts
- Use confidence threshold tuning (`--conf`) to balance false positives/negatives
