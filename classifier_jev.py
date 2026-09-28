import logging
import os

from typesafe_sdk import Noul, TypeSafeClient

_THRESHOLD = float(os.environ.get("RELEVANCE_THRESHOLD", "0.75"))


def classify_score(text: str) -> float:
    try:
        client = TypeSafeClient()
        response = client.system_one(
            state=text,
            questions={
                "relevant": Noul(
                    instructions="This is a genuine racing question, car spec inquiry, schedule question, or handicap question — not banter, race incident chat, or general off-topic conversation",
                )
            },
        )
        return response.answers["relevant"].noul
    except Exception as e:
        logging.warning("Classifier error: %s", e)
        return 0.0


def is_racing_relevant(text: str) -> bool:
    return classify_score(text) >= _THRESHOLD
