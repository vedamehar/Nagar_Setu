# Train and Test the New Multiclass Road-Issue Model (Your Image Data)

This guide shows exact commands to:
- prepare dataset
- train model on GPU
- evaluate model
- test one uploaded image and get issue + severity + priority JSON

---

## 1) Open project folder

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
```

## 2) Use the existing project venv Python

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" --version
```

Use this exact Python for all commands below:

```powershell
$PY = "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe"
```

## 3) Install dependencies (same venv)

```powershell
& $PY -m pip install -r requirements.txt
```

---

## 4) Prepare dataset from your new Roboflow folder

Source dataset path:
`D:/Work/Hack/PVG - App/Dataset/pothole detection_new.v1i.multiclass`

Run:

```powershell
& $PY scripts/prepare_multiclass_dataset.py --source-root "D:/Work/Hack/PVG - App/Dataset/pothole detection_new.v1i.multiclass" --output-root "data/pothole_multiclass_cls"
```

This creates:
- `data/pothole_multiclass_cls/train`
- `data/pothole_multiclass_cls/val`
- `data/pothole_multiclass_cls/test`

with class folders inside each split.

---

## 5) Train on GPU

```powershell
& $PY train_multiclass.py --model yolov8n-cls.pt --data data/pothole_multiclass_cls --epochs 50 --imgsz 224 --batch 32 --device 0 --workers 0 --exist-ok
```

Best checkpoint will be available at:
- `runs/classify/train_multiclass/weights/best.pt`

---

## 6) Evaluate model (accuracy, F1, confusion matrix)

```powershell
& $PY eval_multiclass.py --model "runs/classify/train_multiclass/weights/best.pt" --test-dir "data/pothole_multiclass_cls/test" --device 0 --output-json "runs/classify/eval_multiclass.json"
```

Evaluation JSON:
- `runs/classify/eval_multiclass.json`

---

## 7) Test on one uploaded image (issue + severity)

Replace `YOUR_IMAGE_PATH.jpg` with your image path.

```powershell
& $PY predict_photo_issue_multiclass.py --image "YOUR_IMAGE_PATH.jpg" --model "runs/classify/train_multiclass/weights/best.pt" --device 0 --output-json "runs/classify/single_prediction_multiclass.json"
```

Output JSON:
- `runs/classify/single_prediction_multiclass.json`

---

## 8) View output JSON files

```powershell
Get-Content runs/classify/eval_multiclass.json
Get-Content runs/classify/single_prediction_multiclass.json
```

---

## 9) If you want to train on your own custom image dataset

Use this folder format:

```text
data/my_road_dataset/
  train/
    Pothole/
    Patch/
    object/
  val/
    Pothole/
    Patch/
    object/
  test/
    Pothole/
    Patch/
    object/
```

Then train with:

```powershell
& $PY train_multiclass.py --model yolov8n-cls.pt --data data/my_road_dataset --epochs 50 --imgsz 224 --batch 32 --device 0 --workers 0 --exist-ok
```

Evaluate with:

```powershell
& $PY eval_multiclass.py --model "runs/classify/train_multiclass/weights/best.pt" --test-dir "data/my_road_dataset/test" --device 0 --output-json "runs/classify/eval_my_road_dataset.json"
```

---

## Notes

- This multiclass dataset is image-classification format, not bounding-box detection format.
- So this model predicts image-level issue and severity/priority estimate.
- It does not count multiple potholes by box locations.
- For multiple pothole counting, use detection dataset format (YOLO detection labels with bounding boxes).
