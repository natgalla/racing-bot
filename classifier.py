import logging
import os

from transformers import pipeline

_MODEL = "MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33"
_LABELS = ["racing rules question", "race incident or banter"]
_RACING_LABEL = _LABELS[0]
_THRESHOLD = float(os.environ.get("RELEVANCE_THRESHOLD", "0.8"))
_pipe = pipeline("zero-shot-classification", model=_MODEL)


def classify_score(text: str) -> float:
    try:
        result = _pipe(text, candidate_labels=_LABELS)
        scores = dict(zip(result["labels"], result["scores"]))
        return scores.get(_RACING_LABEL, 0.0)
    except Exception as e:
        logging.warning("Classifier error: %s", e)
        return 0.0


def is_racing_relevant(text: str) -> bool:
    return classify_score(text) >= _THRESHOLD
