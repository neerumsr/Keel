"""The Python hypothesis spec must match src/lib/decider/hypothesis.ts byte for byte."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel.hypothesis import hypotheses, state_text  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main() -> int:
    fixtures = json.loads((ROOT / "artifacts" / "hypothesis-fixtures.json").read_text(encoding="utf-8"))
    bad = 0
    for fx in fixtures:
        if hypotheses(fx["question"]) != fx["hypotheses"]:
            bad += 1
            print("hypothesis mismatch:", fx["hypotheses"][0], "!=", hypotheses(fx["question"])[0])
        if state_text(fx["state"]) != fx["stateText"]:
            bad += 1
            print("state mismatch:", fx["stateText"][:80])
    print(f"{len(fixtures)} fixtures, {bad} mismatches")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
