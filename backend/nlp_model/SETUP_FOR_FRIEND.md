# NLP Model Setup Guide (For Your Friend)

This guide helps your friend run your trained complaint-classification model on another machine.

It supports:
- inference with your already trained model (fastest)
- optional retraining on the same dataset
- JSON output for integration/demo
- CPU-only execution (no GPU required)

---

## 1) What to share from your folder

Share the full folder:

`D:\Work\Hack\PVG - App\Dataset\project\nlp_model`

At minimum, these files/folders must be present:

- `train_nlp.py`
- `infer_nlp.py`
- `predict_complaint_cli.py`
- `check_nlp_setup.py`
- `requirements.txt`
- `model/best_model.pt`
- `model/best_model_metrics.json`
- `tokenizer/` (all files inside)
- `label_encoders.pkl`

If your friend also wants to retrain, include dataset file:

- `civic_nlp_dataset_10000.csv`

---

## 2) Python version

Recommended:
- Python 3.10 to 3.12

Python 3.13 may work, but 3.10/3.11 is usually smoother for ML package compatibility.

---

## 3) Create and activate virtual environment (friend machine)

From inside the shared `nlp_model` folder:

```powershell
python -m venv .venv
```

Windows PowerShell:

```powershell
\.venv\Scripts\Activate.ps1
```

Linux/Mac:

```bash
source .venv/bin/activate
```

---

## 4) Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` already includes:
- transformers
- torch
- scikit-learn
- pandas
- numpy
- tqdm

---

## 5) Run preflight setup check (important)

Run this first to confirm all required files/packages exist.

```powershell
python check_nlp_setup.py --mode all --json-output setup_check_report.json
```

If this command exits with FAIL, fix the missing items listed in the report.

---

## 6) CPU-only inference with trained model (recommended for friend)

Run on CPU explicitly:

```powershell
python predict_complaint_cli.py --text "There is a pothole and water leakage" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device cpu --output-json nlp_predictions_friend.json
```

Output file:
- `nlp_predictions_friend.json`

This gives:
- issue_category
- department
- priority
- response_time
- resolution_time
- confidence scores
- actionable/rejection for nonsense text

---

## 7) CPU-only interactive mode

```powershell
python predict_complaint_cli.py --interactive --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device cpu
```

Type complaint text and press Enter.
Type `exit` to stop.

---

## 8) Optional: CPU-only simple inference script

```powershell
python infer_nlp.py --text "Garbage not collected and dirty public toilet" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device cpu --output-json nlp_predictions_simple.json
```

---

## 9) Optional: retrain model from local CSV (CPU)

If retraining is needed, ensure dataset CSV exists in this same folder:
- `civic_nlp_dataset_10000.csv`

Run training check:

```powershell
python check_nlp_setup.py --mode train
```

Run retraining:

```powershell
python train_nlp.py --model-name distilbert-base-uncased --batch-size 16 --learning-rate 2e-5 --epochs 4 --max-length 128 --workers 0
```

This regenerates:
- `model/best_model.pt`
- `model/best_model_metrics.json`
- `model/training_history.json`
- `tokenizer/`
- `label_encoders.pkl`

---

## 10) Suggested full CPU run sequence (copy-paste)

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python check_nlp_setup.py --mode all --json-output setup_check_report.json
python predict_complaint_cli.py --text "There is a pothole and water leakage" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device cpu --output-json nlp_predictions_friend.json
```

---

## 11) Common issues

---

## 5) Quick check: use your trained model (no retraining)

Run:

```powershell
python predict_complaint_cli.py --text "There is a pothole and water leakage" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto --output-json nlp_predictions_friend.json
```

Output file:
- `nlp_predictions_friend.json`

This gives:
- issue_category
- department
- priority
- response_time
- resolution_time
- confidence scores
- actionable/rejection for nonsense text

---

## 6) Interactive mode (type complaints one by one)

```powershell
python predict_complaint_cli.py --interactive --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto
```

Type complaint text and press Enter.
Type `exit` to stop.

---

## 7) Optional: run simple inference script

```powershell
python infer_nlp.py --text "Garbage not collected and dirty public toilet" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device auto --output-json nlp_predictions_simple.json
```

---

## 8) Optional: retrain model on dataset

If retraining is needed, place dataset CSV in this folder as:
- `civic_nlp_dataset_10000.csv`

Then run:

```powershell
python train_nlp.py --model-name distilbert-base-uncased --batch-size 16 --learning-rate 2e-5 --epochs 4 --max-length 128 --workers 0
```

This regenerates:
- `model/best_model.pt`
- `model/best_model_metrics.json`
- `model/training_history.json`
- `tokenizer/`
- `label_encoders.pkl`

---

## 9) GPU usage

- Use `--device auto` to use CUDA if available.
- Force GPU: `--device cuda`
- Force CPU: `--device cpu`

Examples:

```powershell
python predict_complaint_cli.py --text "Water leakage near road" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device cuda
```

---

### A) `Model checkpoint not found`

Ensure `model/best_model.pt` exists.

### B) `label_encoders.pkl` not found
Ensure the file is present in same folder or pass full path using `--encoders-path`.

### C) CUDA not available
Use `--device auto` or `--device cpu`.

### D) HuggingFace download blocked
First run may need internet to resolve tokenizer/model config. After first successful run, cache is reused.

### E) `check_nlp_setup.py` reports missing files
Copy the missing files into the `nlp_model` folder and run the check again.

---

## 12) Recommended command for demo (CPU)

Use this one command for presentation/demo:

```powershell
python predict_complaint_cli.py --text "There is a pothole and water leakage" --model-dir model --tokenizer-dir tokenizer --encoders-path label_encoders.pkl --device cpu --output-json nlp_predictions_demo.json
```

