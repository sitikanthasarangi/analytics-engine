import os
import json
from pathlib import Path
from typing import List, Dict, Any

# Base paths
DATA_DIR = Path(__file__).parent / "data"
DATASETS_DIR = DATA_DIR / "datasets"
CATALOG_PATH = DATA_DIR / "catalog.json"

DATA_DIR.mkdir(exist_ok=True)
DATASETS_DIR.mkdir(exist_ok=True)


def load_catalog() -> Dict[str, Any]:
    """Load catalog.json if it exists, else return empty catalog."""
    if not CATALOG_PATH.exists():
        return {"datasets": []}
    with open(CATALOG_PATH, "r") as f:
        return json.load(f)


def save_catalog(catalog: Dict[str, Any]) -> None:
    """Persist catalog.json atomically."""
    tmp_path = CATALOG_PATH.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(catalog, f, indent=2)
    os.replace(tmp_path, CATALOG_PATH)


def list_datasets() -> List[Dict[str, Any]]:
    """Return list of dataset entries from catalog."""
    catalog = load_catalog()
    return catalog.get("datasets", [])


def register_dataset(
    name: str,
    filename: str,
    schema: Dict[str, Any],
    kind: str = "file",
) -> None:
    """
    Register or update a dataset in the catalog.

    Args:
        name: logical name (e.g., "orders")
        filename: file name under data/datasets (e.g., "orders.csv") or None for warehouse
        schema: dict with at least {"columns": [...], "rows": int}
        kind: "file" or "warehouse"
    """
    catalog = load_catalog()
    datasets = catalog.get("datasets", [])

    if kind == "file":
        location = f"data/datasets/{filename}"
    else:
        # for warehouse datasets, put real table path in schema["location"]
        location = schema.get("location")

    entry = {
        "name": name,
        "filename": filename,
        "kind": kind,
        "location": location,
        "schema": schema,
    }

    # Update if exists, else append
    for i, ds in enumerate(datasets):
        if ds.get("name") == name:
            datasets[i] = entry
            break
    else:
        datasets.append(entry)

    catalog["datasets"] = datasets
    save_catalog(catalog)
