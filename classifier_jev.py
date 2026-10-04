import logging
import os

from typesafe_sdk import Noul, TypeSafeClient

THRESHOLD = float(os.environ.get("RELEVANCE_THRESHOLD", "0.50"))

_CLIENT = TypeSafeClient()


def classify_score(text: str) -> float:
    try:
        response = _CLIENT.system_one(
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
