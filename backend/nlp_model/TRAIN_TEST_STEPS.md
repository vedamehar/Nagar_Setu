# NLP Model Train and Test Steps (Exact Commands)

This guide gives exact commands to train and test the NLP civic complaint classifier.

## 1) Open PowerShell and move to project

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
```

## 2) Activate the existing environment (same venv)

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\Activate.ps1"
```

## 3) Install dependencies (same environment)

```powershell
pip install -r requirements.txt
pip install -r nlp_model/requirements.txt
```

## 4) Move to nlp_model folder

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project\nlp_model"
```

## 5) Train NLP model (GPU auto, batch 16, lr 2e-5, 4 epochs)

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" train_nlp.py --model-name distilbert-base-uncased --batch-size 16 --learning-rate 2e-5 --epochs 4 --max-length 128 --workers 0
```

Artifacts created:
- model/best_model.pt
- model/best_model_metrics.json
- model/training_history.json
- tokenizer/
- label_encoders.pkl

## 6) Test with single/multi-issue complaint (JSON output)

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" infer_nlp.py --text "There is a pothole and water leakage" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto --output-json nlp_predictions_test1.json
```

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" infer_nlp.py --text "Garbage not collected and dirty public toilet" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto --output-json nlp_predictions_test2.json
```

## 7) Test with confidence scores using the new script

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" predict_complaint_cli.py --text "Large pothole and garbage not collected" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto --output-json nlp_predictions_with_confidence.json
```

## 8) Interactive mode (type new complaints any time)

```powershell
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" predict_complaint_cli.py --interactive --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto
```

Type complaint text and press Enter. Type `exit` to stop.

## 9) Read outputs

```powershell
Get-Content model/best_model_metrics.json
Get-Content nlp_predictions_test1.json
Get-Content nlp_predictions_test2.json
Get-Content nlp_predictions_with_confidence.json
```

## One-shot quick run

```powershell
cd "D:\Work\Hack\PVG - App\Dataset\project"
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\Activate.ps1"
pip install -r requirements.txt
pip install -r nlp_model/requirements.txt
cd "D:\Work\Hack\PVG - App\Dataset\project\nlp_model"
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" train_nlp.py --model-name distilbert-base-uncased --batch-size 16 --learning-rate 2e-5 --epochs 4 --max-length 128 --workers 0
& "D:\Work\Hack\PVG - App\Dataset\.venv\Scripts\python.exe" predict_complaint_cli.py --text "There is a pothole and water leakage" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto --output-json nlp_predictions_with_confidence.json
```
