from __future__ import annotations

import argparse
import json
import sys

from ..services.message_classifier import classify_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify a LINE text message without saving.")
    parser.add_argument("--text", required=True, help="LINE message text to classify.")
    args = parser.parse_args()

    result = classify_text(args.text)
    print(
        json.dumps(
            {
                "message_type": result.message_type,
                "confidence": result.confidence,
                "reason": result.reason,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
