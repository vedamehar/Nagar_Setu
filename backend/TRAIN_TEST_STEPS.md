# Smart Civic Road Issue Detection - Run, Train, and Test Guide

This file gives exact copy-paste commands to run the full pipeline on Windows PowerShell using GPU.

## 1) Open terminal in project folder

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
```

## 2) Activate virtual environment

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\Activate.ps1"
```

## 3) Verify GPU is available

```powershell
nvidia-smi
python -c "import torch; print('Torch:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

Expected: `CUDA available: True` and your GPU name.

## 4) Install dependencies (if not installed)

```powershell
pip install -r requirements.txt
```

If torch is CPU-only in your environment, install CUDA build:

```powershell
pip uninstall -y torch torchvision torchaudio
pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio
```

Re-check GPU:

```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

## 5) Convert XML annotations to YOLO labels (run once)

```powershell
python scripts/convert_xml.py --xml-dir "D:/Work/Hack/PVG - App/Dataset/RDD2022_India/India/train/annotations/xmls" --output-dir "data/raw/annotations"
```

## 6) Split data into train/val (run once, or when re-splitting)

```powershell
python scripts/split_data.py --source-images "D:/Work/Hack/PVG - App/Dataset/RDD2022_India/India/train/images" --source-labels "data/raw/annotations" --output-root "data/dataset" --val-ratio 0.2 --seed 42
```

## 7) Train the model on GPU

```powershell
python train.py --model yolov8n.pt --data data.yaml --epochs 50 --imgsz 640 --batch 16 --device 0 --workers 0
```

Notes:
- `--device 0` forces first GPU.
- `--workers 0` avoids Windows shared memory mapping errors.
- `pin_memory` is disabled by default for stability on Windows.
- Model weights are saved at `runs/detect/train/weights/best.pt`.

## 8) Validate model metrics on GPU

```powershell
yolo detect val model=runs/detect/train/weights/best.pt data=data.yaml device=0
```

This prints mAP, precision, and recall.

## 9) Test (inference) on India test images using GPU

```powershell
python infer.py --model runs/detect/train/weights/best.pt --image-dir "D:/Work/Hack/PVG - App/Dataset/RDD2022_India/India/test/images" --device 0 --save-annotated --output-json runs/infer/predictions.json
```

Outputs:
- JSON predictions: `runs/infer/predictions.json`
- Annotated images: `runs/infer/`

## 10) Read JSON output

```powershell
Get-Content runs/infer/predictions.json
```

## 11) Optional: monitor GPU during training

In another terminal:

```powershell
nvidia-smi -l 2
```

## One-shot quick sequence (copy all)

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\Activate.ps1"
python scripts/convert_xml.py --xml-dir "D:/Work/Hack/PVG - App/Dataset/RDD2022_India/India/train/annotations/xmls" --output-dir "data/raw/annotations"
python scripts/split_data.py --source-images "D:/Work/Hack/PVG - App/Dataset/RDD2022_India/India/train/images" --source-labels "data/raw/annotations" --output-root "data/dataset" --val-ratio 0.2 --seed 42
python train.py --model yolov8n.pt --data data.yaml --epochs 50 --imgsz 640 --batch 16 --device 0 --workers 0
yolo detect val model=runs/detect/train/weights/best.pt data=data.yaml device=0
python infer.py --model runs/detect/train/weights/best.pt --image-dir "D:/Work/Hack/PVG - App/Dataset/RDD2022_India/India/test/images" --device 0 --save-annotated --output-json runs/infer/predictions.json
```
