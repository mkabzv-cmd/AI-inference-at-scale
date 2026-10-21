#!/usr/bin/env python3
"""Compare padded and greedy-packed slot use without claiming model speed."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    maximum = int(config["maximum_sequence_length"])
    lengths = [int(value) for value in config["educational_token_lengths"]]
    if not lengths or any(value < 1 or value > maximum for value in lengths):
        raise SystemExit("every teaching length must be within the sequence limit")
    bins = []
    for length in sorted(lengths, reverse=True):
        for index, used in enumerate(bins):
            if used + length <= maximum:
                bins[index] += length
                break
        else:
            bins.append(length)
    useful = sum(lengths)
    padded_slots = len(lengths) * maximum
    packed_slots = len(bins) * maximum
    report = {
        "schema_version": 1,
        "evidence_kind": "educational-layout-arithmetic-not-throughput",
        "maximum_sequence_length": maximum,
        "lengths": lengths,
        "padded": {
            "sequences": len(lengths),
            "slots": padded_slots,
            "useful_tokens": useful,
            "utilization": useful / padded_slots,
        },
        "greedy_packed": {
            "sequences": len(bins),
            "used_tokens_per_sequence": bins,
            "slots": packed_slots,
            "useful_tokens": useful,
            "utilization": useful / packed_slots,
        },
        "semantic_gate": (
            "A real packing treatment must prove position and attention "
            "isolation before performance comparison."
        ),
        "warning": config["warning"],
    }
    assert packed_slots <= padded_slots
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"PASS: padded utilization={report['padded']['utilization']:.3f}; "
        f"packed utilization={report['greedy_packed']['utilization']:.3f}"
    )


if __name__ == "__main__":
    main()
