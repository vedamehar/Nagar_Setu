# Single Photo Issue Detection and Severity Guide

Use this guide to upload one photo and get:
- detected issue (`pothole` or `damaged_road`)
- severity (`LOW`/`MEDIUM`/`HIGH`)
- priority (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`)
- structured JSON output

## 1) Open project folder

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
```

## 2) Activate existing virtual environment

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\Activate.ps1"
```

## 3) Predict from one uploaded image

Replace `YOUR_IMAGE_PATH.jpg` with your uploaded photo path.

```powershell
python predict_photo_issue.py --image "YOUR_IMAGE_PATH.jpg" --model "runs/detect/runs/train2/weights/best.pt" --device 0 --save-annotated --output-json "runs/infer/single_prediction.json"
```

## 4) Read JSON output

```powershell
Get-Content runs/infer/single_prediction.json
```

## 5) Output fields you get

Example structure:

```json
{
  "image": "D:/path/to/photo.jpg",
  "issue": "pothole",
  "severity": "HIGH",
  "count": 4,
  "priority": "CRITICAL",
  "damage_area_ratio": 0.1734,
  "detections": [
    {
      "class_id": 0,
      "label": "pothole",
      "confidence": 0.92,
      "bbox": [102.4, 220.8, 280.2, 411.6]
    }
  ],
  "annotated_image": "runs/infer/single/photo.jpg"
}
```

## 6) Severity logic used

- if `damage_area_ratio > 0.15` => `HIGH`
- else if `damage_area_ratio > 0.05` => `MEDIUM`
- else => `LOW`
- if object count is greater than 3, severity increases by one level

## 7) Optional: allow CPU fallback

GPU is used by default. If CUDA is unavailable and you still want to run:

```powershell
python predict_photo_issue.py --image "YOUR_IMAGE_PATH.jpg" --model "runs/detect/runs/train2/weights/best.pt" --device auto --allow-cpu --output-json "runs/infer/single_prediction.json"
```
