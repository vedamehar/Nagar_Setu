import argparse
import json
import os
import pickle
import re
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

    return model, tokenizer, encoders, checkpoint


def predict_single(
    text: str,
    model: nn.Module,
    tokenizer: AutoTokenizer,
    encoders: Dict[str, object],
    max_length: int,
    device: torch.device,
) -> Dict[str, str]:
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

    output = {}
    for col in TARGET_COLUMNS:
        pred_idx = int(torch.argmax(logits[col], dim=1).item())
        output[col] = str(encoders[col].inverse_transform([pred_idx])[0])

    return output


def predict_complaint(
    text: str,
    model: nn.Module,
    tokenizer: AutoTokenizer,
    encoders: Dict[str, object],
    max_length: int,
    device: torch.device,
) -> List[Dict[str, str]]:
    parts = split_multi_issue_text(text)
    if not parts:
        parts = [text.strip()]

    results = []
    for part in parts:
        pred = predict_single(part, model, tokenizer, encoders, max_length, device)
        pred["complaint_part"] = part
        results.append(pred)

    return results


def parse_args():
    parser = argparse.ArgumentParser(description="Inference for NLP civic complaint classifier.")
    parser.add_argument("--text", type=str, default="Large pothole and garbage not collected")
    parser.add_argument("--model-dir", type=str, default="model")
    parser.add_argument("--tokenizer-dir", type=str, default="tokenizer")
    parser.add_argument("--encoders-path", type=str, default="label_encoders.pkl")
    parser.add_argument("--output-json", type=str, default="nlp_predictions.json")
    parser.add_argument("--device", type=str, default="auto", help="auto, cpu, or cuda")
    return parser.parse_args()


def resolve_device(device_arg: str) -> torch.device:
    if device_arg == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device_arg == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available.")
    return torch.device(device_arg)


def main() -> None:
    args = parse_args()
    if not args.text or not args.text.strip():
        raise ValueError("Please provide a non-empty complaint text.")

    if os.name == "nt":
        try:
            torch.multiprocessing.set_sharing_strategy("file_system")
        except RuntimeError:
            pass

    device = resolve_device(args.device)

    model, tokenizer, encoders, checkpoint = load_assets(
        args.model_dir,
        args.tokenizer_dir,
        args.encoders_path,
        device,
    )

    max_length = int(checkpoint.get("max_length", 128))
    predictions = predict_complaint(
        text=args.text,
        model=model,
        tokenizer=tokenizer,
        encoders=encoders,
        max_length=max_length,
        device=device,
    )

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2)

    print(json.dumps(predictions, indent=2))
    print(f"Saved predictions to: {args.output_json}")


if __name__ == "__main__":
    main()
