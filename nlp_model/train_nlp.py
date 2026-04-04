import argparse
import json
import os
import pickle
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer


TARGET_COLUMNS = [
    "issue_category",
    "department",
    "priority",
    "response_time",
    "resolution_time",
]

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LOCAL_DATASET = SCRIPT_DIR / "civic_nlp_dataset_10000.csv"


@dataclass
class TrainConfig:
    dataset_path: str
    model_name: str
    max_length: int
    batch_size: int
    learning_rate: float
    epochs: int
    seed: int
    val_size: float
    output_dir: str
    tokenizer_dir: str
    encoders_path: str
    workers: int


class ComplaintDataset(Dataset):
    def __init__(
        self,
        texts: List[str],
        labels: Dict[str, np.ndarray],
        tokenizer: AutoTokenizer,
        max_length: int,
    ) -> None:
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        encoded = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
        }
        for col in TARGET_COLUMNS:
            item[col] = torch.tensor(self.labels[col][idx], dtype=torch.long)
        return item


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
        logits = {col: head(cls_embedding) for col, head in self.heads.items()}
        return logits


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def parse_args() -> TrainConfig:
    parser = argparse.ArgumentParser(description="Train NLP multi-output civic classifier.")
    parser.add_argument(
        "--dataset-path",
        default="civic_nlp_dataset_10000.csv",
        help="Path to civic CSV dataset. Defaults to nlp_model/civic_nlp_dataset_10000.csv.",
    )
    parser.add_argument("--model-name", default="distilbert-base-uncased")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-size", type=float, default=0.2)
    parser.add_argument("--output-dir", default="model")
    parser.add_argument("--tokenizer-dir", default="tokenizer")
    parser.add_argument("--encoders-path", default="label_encoders.pkl")
    parser.add_argument("--workers", type=int, default=0)
    args = parser.parse_args()

    return TrainConfig(
        dataset_path=args.dataset_path,
        model_name=args.model_name,
        max_length=args.max_length,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        epochs=args.epochs,
        seed=args.seed,
        val_size=args.val_size,
        output_dir=args.output_dir,
        tokenizer_dir=args.tokenizer_dir,
        encoders_path=args.encoders_path,
        workers=args.workers,
    )


def resolve_dataset_path(dataset_path: str) -> Path:
    candidate = Path(dataset_path)

    if candidate.is_absolute() and candidate.exists():
        return candidate

    if candidate.exists():
        return candidate.resolve()

    from_script_dir = (SCRIPT_DIR / candidate).resolve()
    if from_script_dir.exists():
        return from_script_dir

    if not dataset_path.strip() and DEFAULT_LOCAL_DATASET.exists():
        return DEFAULT_LOCAL_DATASET

    raise FileNotFoundError(
        "Dataset CSV not found. Checked: "
        f"{candidate.resolve()} and {from_script_dir}. "
        "Place civic_nlp_dataset_10000.csv inside nlp_model or pass --dataset-path explicitly."
    )


def load_and_prepare_data(dataset_path: str) -> Tuple[pd.DataFrame, Dict[str, LabelEncoder]]:
    df = pd.read_csv(dataset_path)
    expected = {"complaint", *TARGET_COLUMNS}
    missing = expected.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df[["complaint", *TARGET_COLUMNS]].copy()
    df["complaint"] = df["complaint"].fillna("").astype(str).str.strip()
    for col in TARGET_COLUMNS:
        df[col] = df[col].fillna("UNKNOWN").astype(str).str.strip()

    df = df[df["complaint"] != ""].reset_index(drop=True)
    if df.empty:
        raise ValueError("Dataset has no valid complaint text after preprocessing.")

    encoders: Dict[str, LabelEncoder] = {}
    for col in TARGET_COLUMNS:
        encoder = LabelEncoder()
        df[col] = encoder.fit_transform(df[col])
        encoders[col] = encoder

    return df, encoders


def build_loaders(
    df: pd.DataFrame,
    tokenizer: AutoTokenizer,
    max_length: int,
    batch_size: int,
    val_size: float,
    seed: int,
    workers: int,
) -> Tuple[DataLoader, DataLoader, Dict[str, int]]:
    train_df, val_df = train_test_split(
        df,
        test_size=val_size,
        random_state=seed,
        stratify=df["issue_category"],
    )

    train_labels = {col: train_df[col].to_numpy() for col in TARGET_COLUMNS}
    val_labels = {col: val_df[col].to_numpy() for col in TARGET_COLUMNS}

    train_ds = ComplaintDataset(
        texts=train_df["complaint"].tolist(),
        labels=train_labels,
        tokenizer=tokenizer,
        max_length=max_length,
    )
    val_ds = ComplaintDataset(
        texts=val_df["complaint"].tolist(),
        labels=val_labels,
        tokenizer=tokenizer,
        max_length=max_length,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=workers,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=workers,
    )

    num_labels_per_head = {col: int(df[col].nunique()) for col in TARGET_COLUMNS}
    return train_loader, val_loader, num_labels_per_head


def evaluate(
    model: nn.Module,
    data_loader: DataLoader,
    device: torch.device,
) -> Dict[str, Dict[str, float]]:
    model.eval()
    y_true = {col: [] for col in TARGET_COLUMNS}
    y_pred = {col: [] for col in TARGET_COLUMNS}

    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            logits = model(input_ids=input_ids, attention_mask=attention_mask)

            for col in TARGET_COLUMNS:
                preds = torch.argmax(logits[col], dim=1).cpu().numpy().tolist()
                labels = batch[col].cpu().numpy().tolist()
                y_pred[col].extend(preds)
                y_true[col].extend(labels)

    metrics: Dict[str, Dict[str, float]] = {}
    macro_f1_values = []
    for col in TARGET_COLUMNS:
        acc = accuracy_score(y_true[col], y_pred[col])
        f1 = f1_score(y_true[col], y_pred[col], average="weighted", zero_division=0)
        precision = precision_score(y_true[col], y_pred[col], average="weighted", zero_division=0)
        recall = recall_score(y_true[col], y_pred[col], average="weighted", zero_division=0)
        metrics[col] = {
            "accuracy": float(acc),
            "f1_weighted": float(f1),
            "precision_weighted": float(precision),
            "recall_weighted": float(recall),
        }
        macro_f1_values.append(f1)

    metrics["overall"] = {
        "mean_f1_weighted": float(np.mean(macro_f1_values)),
        "heads": len(TARGET_COLUMNS),
    }
    return metrics


def train_epoch(
    model: nn.Module,
    data_loader: DataLoader,
    optimizer: AdamW,
    device: torch.device,
    loss_fn: nn.Module,
) -> float:
    model.train()
    running_loss = 0.0

    progress = tqdm(data_loader, desc="Train", leave=False)
    for batch in progress:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)

        logits = model(input_ids=input_ids, attention_mask=attention_mask)
        loss = 0.0
        for col in TARGET_COLUMNS:
            targets = batch[col].to(device)
            loss = loss + loss_fn(logits[col], targets)

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        progress.set_postfix(loss=f"{loss.item():.4f}")

    return running_loss / max(len(data_loader), 1)


def save_artifacts(
    model: MultiHeadDistilBERT,
    tokenizer: AutoTokenizer,
    encoders: Dict[str, LabelEncoder],
    config: TrainConfig,
    num_labels_per_head: Dict[str, int],
    best_epoch: int,
    best_metrics: Dict[str, Dict[str, float]],
    history: List[Dict[str, object]],
) -> None:
    output_dir = Path(config.output_dir)
    tokenizer_dir = Path(config.tokenizer_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "state_dict": model.state_dict(),
        "model_name": config.model_name,
        "num_labels_per_head": num_labels_per_head,
        "target_columns": TARGET_COLUMNS,
        "max_length": config.max_length,
    }
    torch.save(checkpoint, output_dir / "best_model.pt")

    label_maps = {
        col: [str(v) for v in encoders[col].classes_.tolist()] for col in TARGET_COLUMNS
    }

    with open(output_dir / "best_model_metrics.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "best_epoch": best_epoch,
                "best_metrics": best_metrics,
                "model_checkpoint": str((output_dir / "best_model.pt").resolve()),
                "label_mappings": label_maps,
            },
            f,
            indent=2,
        )

    with open(output_dir / "training_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    tokenizer.save_pretrained(tokenizer_dir)

    with open(config.encoders_path, "wb") as f:
        pickle.dump(encoders, f)


def main() -> None:
    config = parse_args()
    set_seed(config.seed)

    if os.name == "nt":
        # Prevent Windows shared-memory mapping issues in dataloaders.
        try:
            torch.multiprocessing.set_sharing_strategy("file_system")
        except RuntimeError:
            pass

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    dataset_path = resolve_dataset_path(config.dataset_path)
    print(f"Dataset: {dataset_path}")
    df, encoders = load_and_prepare_data(str(dataset_path))
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)

    train_loader, val_loader, num_labels_per_head = build_loaders(
        df=df,
        tokenizer=tokenizer,
        max_length=config.max_length,
        batch_size=config.batch_size,
        val_size=config.val_size,
        seed=config.seed,
        workers=config.workers,
    )

    model = MultiHeadDistilBERT(config.model_name, num_labels_per_head).to(device)
    optimizer = AdamW(model.parameters(), lr=config.learning_rate)
    loss_fn = nn.CrossEntropyLoss()

    history: List[Dict[str, object]] = []
    best_score = -1.0
    best_state = None
    best_epoch = -1
    best_metrics: Dict[str, Dict[str, float]] = {}

    for epoch in range(1, config.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device, loss_fn)
        metrics = evaluate(model, val_loader, device)
        val_score = metrics["overall"]["mean_f1_weighted"]

        record = {
            "epoch": epoch,
            "train_loss": float(train_loss),
            "val_metrics": metrics,
        }
        history.append(record)

        print(
            f"Epoch {epoch}/{config.epochs} | "
            f"train_loss={train_loss:.4f} | "
            f"val_mean_f1={val_score:.4f}"
        )

        if val_score > best_score:
            best_score = val_score
            best_epoch = epoch
            best_metrics = metrics
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is None:
        raise RuntimeError("Training did not produce a best model state.")

    model.load_state_dict(best_state)

    save_artifacts(
        model=model,
        tokenizer=tokenizer,
        encoders=encoders,
        config=config,
        num_labels_per_head=num_labels_per_head,
        best_epoch=best_epoch,
        best_metrics=best_metrics,
        history=history,
    )

    print("Training complete.")
    print(f"Best epoch: {best_epoch}")
    print(f"Best mean weighted F1: {best_score:.4f}")
    print(f"Model saved to: {Path(config.output_dir) / 'best_model.pt'}")


if __name__ == "__main__":
    main()
