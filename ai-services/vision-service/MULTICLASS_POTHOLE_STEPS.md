# Multiclass Pothole Dataset Pipeline (Train, Evaluate, Predict)

This guide uses your new dataset at:

D:/Work/Hack/PVG - App/Dataset/pothole detection_new.v1i.multiclass

Important:
- This dataset is image classification format (`_classes.csv`), not bounding-box detection labels.
- It can classify image-level issue type (`Pothole`, `Patch`, `object`).
- It cannot directly count multiple potholes or compute area-based severity from boxes.

## 1) Open project and activate environment

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\Activate.ps1"
```

## 2) Prepare class-folder dataset for YOLO classification

```powershell
& "D:/Work/Hack/PVG - App/Dataset/.venv/Scripts/python.exe" scripts/prepare_multiclass_dataset.py --source-root "D:/Work/Hack/PVG - App/Dataset/pothole detection_new.v1i.multiclass" --output-root "data/pothole_multiclass_cls"
```

Output layout created:
- data/pothole_multiclass_cls/train/<class_name>/*.jpg
- data/pothole_multiclass_cls/val/<class_name>/*.jpg
- data/pothole_multiclass_cls/test/<class_name>/*.jpg

## 3) Train the multiclass model on GPU

```powershell
& "D:/Work/Hack/PVG - App/Dataset/.venv/Scripts/python.exe" train_multiclass.py --model yolov8n-cls.pt --data data/pothole_multiclass_cls --epochs 50 --imgsz 224 --batch 32 --device 0 --workers 0 --exist-ok
```

Best weights will be at:
- runs/classify/train_multiclass/weights/best.pt

## 4) Evaluate model on test set

```powershell
& "D:/Work/Hack/PVG - App/Dataset/.venv/Scripts/python.exe" eval_multiclass.py --model "runs/classify/train_multiclass/weights/best.pt" --test-dir "data/pothole_multiclass_cls/test" --device 0 --output-json "runs/classify/eval_multiclass.json"
```

Evaluation JSON includes:
- accuracy
- weighted F1
- macro F1
- confusion matrix
- per-class precision/recall/F1

## 5) Predict issue + severity from one uploaded image

```powershell
& "D:/Work/Hack/PVG - App/Dataset/.venv/Scripts/python.exe" predict_photo_issue_multiclass.py --image "D:/path/to/uploaded_photo.jpg" --model "runs/classify/train_multiclass/weights/best.pt" --device auto --output-json "runs/classify/single_prediction_multiclass.json"
```

Output fields:
- predicted_class
- class_confidence
- issue
- severity
- priority

Severity in this classifier pipeline is confidence-based:
- confidence >= 0.85 -> HIGH
- confidence >= 0.60 -> MEDIUM
- else -> LOW

`object` class is mapped to:
- issue = no_road_issue
- severity = NONE
- priority = LOW

## 6) If you need true multiple pothole counting + size severity

Use your detection pipeline (`train.py`, `infer.py`, `predict_photo_issue.py`) with a bounding-box dataset.
This multiclass dataset cannot provide box-level count/area because annotations are image-level labels.

For true multiple pothole detection on this same Roboflow source, re-export it as Object Detection (YOLO format) with bounding boxes and then retrain with:

```powershell
& "D:/Work/Hack/PVG - App/Dataset/.venv/Scripts/python.exe" train.py --model yolov8n.pt --data data.yaml --epochs 50 --imgsz 640 --batch 16 --device 0 --workers 0
```
