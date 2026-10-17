"""Local vision relevance: CLIP zero-shot classification, fully offline.

Gives ReelForge its own eyes. No API key, no quota, no network — a candidate
clip's middle frame is scored against the scene's query vs. a set of generic
confuser labels. Used as the relevance gate when the Gemini vision check is
unavailable (and as a pre-filter before spending Gemini calls).
"""

from __future__ import annotations

import functools
from pathlib import Path

# Generic confusers covering the bulk of stock-index mismatches. Broad
# categories, not whack-a-mole: a wrong clip is almost always one of these.
NEGATIVE_LABELS = [
    "a hamburger or burger",
    "a green plant or leaves",
    "a bird or animal",
    "a landscape or beach",
    "people walking on a street",
    "oranges or citrus fruit",
    "milk being poured into a glass",
    "an empty cooking pan",
    "a dessert or cake",
    "pasta",
    "a car or traffic",
    "a building or architecture",
    "cutlery, spoons and forks",
    "a farm field or crops",
    "a wine glass",
]


MODEL_ID = "openai/clip-vit-base-patch32"
MODEL_FILES = [
    "config.json", "preprocessor_config.json", "pytorch_model.bin",
    "tokenizer.json", "tokenizer_config.json", "vocab.json",
    "merges.txt", "special_tokens_map.json",
]


def model_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "models" / "clip-vit-base-patch32"


def ensure_model() -> Path:
    """Download the CLIP model on first use. Returns the directory."""
    d = model_dir()
    missing = [f for f in MODEL_FILES if not (d / f).exists()]
    if not missing:
        return d
    d.mkdir(parents=True, exist_ok=True)
    print(f"vision: downloading CLIP model ({len(missing)} files)…")
    import urllib.request
    for f in missing:
        url = f"https://huggingface.co/{MODEL_ID}/resolve/main/{f}"
        urllib.request.urlretrieve(url, d / f)
    return d


@functools.lru_cache(maxsize=1)
def _model():
    from transformers import CLIPProcessor, CLIPModel
    src = str(ensure_model())  # downloads on first use
    model = CLIPModel.from_pretrained(src)
    processor = CLIPProcessor.from_pretrained(src)
    model.eval()
    return model, processor


def score_frame(frame: Path, labels: list[str]) -> dict[str, float]:
    """Softmax scores of the frame against each text label."""
    import torch
    from PIL import Image

    model, processor = _model()
    image = Image.open(frame).convert("RGB")
    inputs = processor(text=labels, images=image, return_tensors="pt",
                       padding=True)
    with torch.no_grad():
        out = model(**inputs)
    probs = out.logits_per_image.softmax(dim=1)[0]
    return {label: float(probs[i]) for i, label in enumerate(labels)}


def relevant(frame: Path, query: str, margin: float = 0.0) -> tuple[bool, str, float]:
    """True when the frame looks more like `query` than any confuser.

    Returns (is_relevant, best_label, best_score).
    """
    positives = [f"a photo of {query}", f"{query} food"]
    labels = positives + NEGATIVE_LABELS
    scores = score_frame(frame, labels)
    best_pos = max(scores[l] for l in positives)
    best_neg = max(scores[l] for l in NEGATIVE_LABELS)
    best_label = max(scores, key=scores.get)  # type: ignore[arg-type]
    return (best_pos > best_neg + margin), best_label, scores[best_label]
