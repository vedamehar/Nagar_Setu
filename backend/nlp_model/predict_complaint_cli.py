import argparse
import json
import os
import pickle
import re
import string
from pathlib import Path
from typing import Dict, List

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer


TARGET_COLUMNS = [
    "issue_category",
    "department",
    "priority",
    "response_time",
    "resolution_time",
]

# Domain keywords used to validate whether a complaint is civic-service related.
CIVIC_KEYWORDS = {
    "pothole",
    "road",
    "crack",
    "garbage",
    "waste",
    "drain",
    "drainage",
    "sewer",
    "sewage",
    "water",
    "leak",
    "leakage",
    "electric",
    "electricity",
    "streetlight",
    "street",
    "toilet",
    "sanitation",
    "flood",
    "traffic",
    "signal",
    "manhole",
}


class MultiHeadDistilBERT(nn.Module):
    def __init__(self, model_name: str, num_labels_per_head: Dict[str, int]) -> None:
        super().__init__()
        self.backbone = AutoModel.from_pretrained(model_name)
        hidden_size = self.backbone.config.hidden_size
        self.dropout = nn.Dropout(0.2)
        self.heads = nn.ModuleDict(
            {col: nn.Linear(hidden_size, n) for col, n in num_labels_per_head.items()}
        )

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> Dict[str, torch.Tensor]:
        outputs = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        cls_embedding = outputs.last_hidden_state[:, 0]
        cls_embedding = self.dropout(cls_embedding)
        return {col: head(cls_embedding) for col, head in self.heads.items()}


def split_multi_issue_text(text: str) -> List[str]:
    parts = re.split(r"\s*(?:,|\band\b|\balso\b)\s*", text, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p and p.strip()]


def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _is_potentially_nonsense(text: str) -> (bool, str):
    stripped = text.strip()
    if not stripped:
        return True, "empty_text"

    words = _tokenize_words(stripped)
    if len(words) < 2:
        return True, "too_short_or_fragment"
    if len(words) == 2 and not _has_civic_signal(stripped):
        return True, "too_short_or_fragment"

    chars = [c for c in stripped if not c.isspace()]
    if not chars:
        return True, "empty_text"

    alpha_count = sum(1 for c in chars if c.isalpha())
    alpha_ratio = alpha_count / len(chars)
    if alpha_ratio < 0.55:
        return True, "too_many_non_letters"

    unique_chars = len(set(stripped.lower()))
    if unique_chars <= 3 and len(stripped) > 8:
        return True, "repetitive_characters"

    vowel_count = sum(1 for c in stripped.lower() if c in "aeiou")
    if vowel_count == 0:
        return True, "no_vowel_signal"

    return False, ""


def _has_civic_signal(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in CIVIC_KEYWORDS)


def _build_rejected_output(part: str, reason: str, confidence: Dict[str, float] | None = None) -> Dict[str, object]:
    return {
        "issue_category": None,
        "department": None,
        "priority": None,
        "response_time": None,
        "resolution_time": None,
        "actionable": False,
        "rejection_reason": reason,
        "confidence": confidence or {},
        "mean_confidence": 0.0 if not confidence else round(
            sum(confidence.values()) / max(len(confidence), 1), 4
        ),
        "complaint_part": part,
    }


def _should_reject_prediction(part: str, pred: Dict[str, object]) -> (bool, str):
    conf_map = pred.get("confidence", {}) if isinstance(pred.get("confidence", {}), dict) else {}
    mean_conf = float(pred.get("mean_confidence", 0.0))
    issue_conf = float(conf_map.get("issue_category_confidence", 0.0))
    dept_conf = float(conf_map.get("department_confidence", 0.0))

    # Always reject very uncertain outputs.
    if mean_conf < 0.45:
        return True, "low_model_confidence"

    civic_signal = _has_civic_signal(part)
    # If text has no civic intent and confidence is not very high, reject assignment.
    if not civic_signal and mean_conf < 0.72:
        return True, "non_civic_or_nonsensical_text"

    # Additional safety guard: weak class routing confidence.
    if issue_conf < 0.35 and dept_conf < 0.35:
        return True, "weak_issue_department_confidence"

    return False, ""


def resolve_device(device_arg: str) -> torch.device:
    if device_arg == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device_arg == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available.")
    return torch.device(device_arg)


def load_assets(model_dir: str, tokenizer_dir: str, encoders_path: str, device: torch.device):
    checkpoint_path = Path(model_dir) / "best_model.pt"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Model checkpoint not found: {checkpoint_path}")

    with open(encoders_path, "rb") as f:
        encoders = pickle.load(f)

    checkpoint = torch.load(checkpoint_path, map_location=device)
    model_name = checkpoint["model_name"]
    num_labels_per_head = checkpoint["num_labels_per_head"]

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir)
    model = MultiHeadDistilBERT(model_name, num_labels_per_head)
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device)
    model.eval()

    return model, tokenizer, encoders, int(checkpoint.get("max_length", 128))


def predict_single_with_confidence(
    text: str,
    model: nn.Module,
    tokenizer: AutoTokenizer,
    encoders: Dict[str, object],
    max_length: int,
    device: torch.device,
) -> Dict[str, object]:
    encoded = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt",
    )
    input_ids = encoded["input_ids"].to(device)
    attention_mask = encoded["attention_mask"].to(device)

    with torch.no_grad():
        logits = model(input_ids=input_ids, attention_mask=attention_mask)

    result: Dict[str, object] = {}
    confidence_map: Dict[str, float] = {}

    for col in TARGET_COLUMNS:
        probs = torch.softmax(logits[col], dim=1)
        conf_value, pred_idx = torch.max(probs, dim=1)

        pred_idx_int = int(pred_idx.item())
        conf_float = float(conf_value.item())
        pred_label = str(encoders[col].inverse_transform([pred_idx_int])[0])

        result[col] = pred_label
        confidence_map[f"{col}_confidence"] = round(conf_float, 4)

    mean_conf = sum(confidence_map.values()) / max(len(confidence_map), 1)
    result["confidence"] = confidence_map
    result["mean_confidence"] = round(float(mean_conf), 4)
    return result


def predict_complaint(
    text: str,
    model: nn.Module,
    tokenizer: AutoTokenizer,
    encoders: Dict[str, object],
    max_length: int,
    device: torch.device,
) -> List[Dict[str, object]]:
    parts = split_multi_issue_text(text)
    if not parts:
        parts = [text.strip()]

    outputs: List[Dict[str, object]] = []
    for part in parts:
        is_bad_text, bad_reason = _is_potentially_nonsense(part)
        if is_bad_text:
            outputs.append(_build_rejected_output(part, bad_reason))
            continue

        pred = predict_single_with_confidence(part, model, tokenizer, encoders, max_length, device)
        reject_pred, reject_reason = _should_reject_prediction(part, pred)
        if reject_pred:
            outputs.append(_build_rejected_output(part, reject_reason, pred.get("confidence", {})))
            continue

        pred["actionable"] = True
        pred["rejection_reason"] = None
        pred["complaint_part"] = part
        outputs.append(pred)

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict civic complaint fields with confidence scores."
    )
    parser.add_argument("--text", type=str, default="")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--model-dir", type=str, default="model")
    parser.add_argument("--tokenizer-dir", type=str, default="tokenizer")
    parser.add_argument("--encoders-path", type=str, default="label_encoders.pkl")
    parser.add_argument("--device", type=str, default="auto", help="auto, cpu, or cuda")
    parser.add_argument(
        "--output-json",
        type=str,
        default="nlp_predictions_with_confidence.json",
        help="Output file used in non-interactive mode.",
    )
    return parser.parse_args()


def run_single(args: argparse.Namespace, device: torch.device) -> None:
    if not args.text or not args.text.strip():
        raise ValueError("Please provide --text for non-interactive mode.")

    model, tokenizer, encoders, max_length = load_assets(
        args.model_dir, args.tokenizer_dir, args.encoders_path, device
    )
    predictions = predict_complaint(
        args.text,
        model,
        tokenizer,
        encoders,
        max_length,
        device,
    )

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2)

    print(json.dumps(predictions, indent=2))
    print(f"Saved predictions to: {args.output_json}")


def run_interactive(args: argparse.Namespace, device: torch.device) -> None:
    model, tokenizer, encoders, max_length = load_assets(
        args.model_dir, args.tokenizer_dir, args.encoders_path, device
    )

    print("Interactive prediction mode. Type your complaint and press Enter.")
    print("Type 'exit' to quit.\n")

    while True:
        text = input("Complaint: ").strip()
        if text.lower() == "exit":
            print("Exiting interactive mode.")
            break
        if not text:
            print("Please enter a non-empty complaint.\n")
            continue

        predictions = predict_complaint(
            text,
            model,
            tokenizer,
            encoders,
            max_length,
            device,
        )
        print(json.dumps(predictions, indent=2))
        print("")


def main() -> None:
    args = parse_args()

    if os.name == "nt":
        try:
            torch.multiprocessing.set_sharing_strategy("file_system")
        except RuntimeError:
            pass

    device = resolve_device(args.device)
    print(f"Using device: {device}")

    if args.interactive:
        run_interactive(args, device)
    else:
        run_single(args, device)


if __name__ == "__main__":
    main()
