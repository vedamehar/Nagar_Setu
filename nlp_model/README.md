# NLP Civic Issue Classification (DistilBERT)

This module trains a multi-output NLP classifier for civic complaints and predicts:
- issue_category
- department
- priority
- response_time
- resolution_time

## Folder Structure

- train_nlp.py
- infer_nlp.py
- requirements.txt
- model/
- tokenizer/
- label_encoders.pkl

## Dataset

CSV path used by default:
- civic_nlp_dataset_10000.csv (inside nlp_model folder)

Required columns:
- complaint
- issue_category
- department
- priority
- response_time
- resolution_time

## Install Dependencies (same existing venv)

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\Activate.ps1"
pip install -r nlp_model/requirements.txt
```

## Train (GPU if available)

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project\nlp_model"
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" train_nlp.py --model-name distilbert-base-uncased --batch-size 16 --learning-rate 2e-5 --epochs 4 --max-length 128 --workers 0
```

## Artifacts Generated

- model/best_model.pt
- model/best_model_metrics.json
- model/training_history.json
- tokenizer/
- label_encoders.pkl

## Test Inference

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project\nlp_model"
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" infer_nlp.py --text "Large pothole and garbage not collected" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto --output-json nlp_predictions.json
```

## Multi-Issue Handling

The inference script splits user text on:
- and
- comma (,)
- also

Each part is predicted separately and returned in structured JSON.

## Example Output JSON

```json
[
  {
    "issue_category": "Roads",
    "department": "PMC Roads",
    "priority": "A1 (High)",
    "response_time": "1 hour",
    "resolution_time": "6 hours",
    "complaint_part": "Large pothole"
  },
  {
    "issue_category": "Sanitation",
    "department": "Solid Waste Management",
    "priority": "A2 (Medium)",
    "response_time": "4 hours",
    "resolution_time": "24 hours",
    "complaint_part": "garbage not collected"
  }
]
```

## Extra Test Samples

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" infer_nlp.py --text "There is a pothole and water leakage" --device auto
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" infer_nlp.py --text "Garbage not collected and dirty public toilet" --device auto
```
