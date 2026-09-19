import logging
import os

from huggingface_hub import InferenceClient

_MODEL = "MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33"
_LABELS = ["racing question or spec inquiry", "race incident or banter"]
_RACING_LABEL = _LABELS[0]
_THRESHOLD = float(os.environ.get("RELEVANCE_THRESHOLD", "0.75"))


def classify_score(text: str) -> float:
    try:
        client = InferenceClient(token=os.environ.get("HF_TOKEN"))
        result = client.zero_shot_classification(text, candidate_labels=_LABELS, model=_MODEL)
        scores = {item.label: item.score for item in result}
        return scores.get(_RACING_LABEL, 0.0)
    except Exception as e:
        logging.warning("Classifier error: %s", e)
        return 0.0


def is_racing_relevant(text: str) -> bool:
    return classify_score(text) >= _THRESHOLD
