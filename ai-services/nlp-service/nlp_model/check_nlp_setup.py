import argparse
import importlib
import json
import platform
import sys
from pathlib import Path


def _check_python_version() -> dict:
    v = sys.version_info
    ok = (v.major == 3) and (10 <= v.minor <= 13)
    msg = f"Python {v.major}.{v.minor}.{v.micro}"
    if not ok:
        msg += " (recommended: 3.10 to 3.12)"
    return {"name": "python_version", "ok": ok, "message": msg}


def _check_package(name: str) -> dict:
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", "unknown")
        return {"name": f"package:{name}", "ok": True, "message": f"installed ({version})"}
    except Exception as exc:  # noqa: BLE001
        return {"name": f"package:{name}", "ok": False, "message": f"missing ({exc})"}


def _check_file(path: Path, label: str) -> dict:
    exists = path.exists()
    return {
        "name": f"file:{label}",
        "ok": exists,
        "message": str(path) if exists else f"missing: {path}",
    }


def _check_dir(path: Path, label: str) -> dict:
    exists = path.exists() and path.is_dir()
    return {
        "name": f"dir:{label}",
        "ok": exists,
        "message": str(path) if exists else f"missing directory: {path}",
    }


def _check_cpu_torch() -> dict:
    try:
        import torch

        msg = "CPU execution available"
        if torch.cuda.is_available():
            msg += "; CUDA is also available (you can still force CPU with --device cpu)"
        return {"name": "cpu_runtime", "ok": True, "message": msg}
    except Exception as exc:  # noqa: BLE001
        return {"name": "cpu_runtime", "ok": False, "message": f"torch import failed: {exc}"}


def run_checks(mode: str, base_dir: Path) -> list:
    checks = []

    checks.append(_check_python_version())
    checks.append({"name": "platform", "ok": True, "message": platform.platform()})

    for pkg in ["transformers", "torch", "sklearn", "pandas", "numpy", "tqdm"]:
        checks.append(_check_package(pkg))

    checks.append(_check_cpu_torch())

    # Common files for all workflows.
    checks.append(_check_file(base_dir / "predict_complaint_cli.py", "predict_script"))
    checks.append(_check_file(base_dir / "infer_nlp.py", "infer_script"))
    checks.append(_check_file(base_dir / "train_nlp.py", "train_script"))
    checks.append(_check_file(base_dir / "requirements.txt", "requirements"))

    if mode in {"all", "train"}:
        checks.append(_check_file(base_dir / "civic_nlp_dataset_10000.csv", "dataset_csv"))

    if mode in {"all", "infer"}:
        checks.append(_check_dir(base_dir / "model", "model_dir"))
        checks.append(_check_file(base_dir / "model" / "best_model.pt", "best_model"))
        checks.append(_check_dir(base_dir / "tokenizer", "tokenizer_dir"))
        checks.append(_check_file(base_dir / "label_encoders.pkl", "label_encoders"))

    return checks


def print_report(checks: list) -> bool:
    all_ok = True
    print("NLP setup preflight report")
    print("-" * 72)
    for item in checks:
        status = "OK" if item["ok"] else "FAIL"
        print(f"[{status}] {item['name']}: {item['message']}")
        if not item["ok"]:
            all_ok = False
    print("-" * 72)
    if all_ok:
        print("Result: PASS (ready to run on CPU)")
    else:
        print("Result: FAIL (fix missing items above)")
    return all_ok


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check NLP setup before training/inference (CPU-friendly)."
    )
    parser.add_argument(
        "--mode",
        choices=["all", "train", "infer"],
        default="all",
        help="Check all requirements, train-only, or infer-only.",
    )
    parser.add_argument(
        "--json-output",
        default="",
        help="Optional path to save the report as JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    checks = run_checks(args.mode, base_dir)
    ok = print_report(checks)

    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"mode": args.mode, "ok": ok, "checks": checks}, f, indent=2)
        print(f"Saved report JSON: {out_path}")

    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
