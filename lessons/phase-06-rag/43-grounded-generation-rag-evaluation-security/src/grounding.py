#!/usr/bin/env python3
"""Safe context assembly, deterministic extraction, citations, and evaluation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

LESSON = Path(__file__).resolve().parents[1]
PHASE = LESSON.parent
L42_SRC = PHASE / "42-retrieval-hybrid-reranking/src"
sys.path.insert(0, str(L42_SRC))

from retrieval import Retriever, tokenize, validate_config  # noqa: E402

SENTENCE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "after",
    "before",
    "do",
    "does",
    "how",
    "is",
    "it",
    "of",
    "the",
    "to",
    "what",
    "when",
    "which",
}
TIME_WORDS = {
    "hour",
    "hours",
    "minute",
    "minutes",
    "day",
    "days",
    "weekday",
    "weekdays",
    "utc",
}


def validate_grounding_config(config: dict[str, Any]) -> None:
    errors = []
    if config.get("retrieval_method") not in {
        "sparse",
        "dense",
        "hybrid",
        "reranked",
    }:
        errors.append("unknown retrieval_method")
    if config.get("injection_action") != "block_chunk":
        errors.append("injection_action must be block_chunk")
    if not isinstance(config.get("injection_patterns"), list) or not config.get(
        "injection_patterns"
    ):
        errors.append("injection_patterns must be a non-empty list")
    if not isinstance(config.get("context_max_words"), int) or not (
        10 <= config.get("context_max_words", 0) <= 2000
    ):
        errors.append("context_max_words must be between 10 and 2000")
    if not isinstance(config.get("retrieval_top_k"), int) or config.get(
        "retrieval_top_k", 0
    ) < 1:
        errors.append("retrieval_top_k must be positive")
    if not isinstance(config.get("minimum_sentence_score"), (int, float)) or config.get(
        "minimum_sentence_score", 0
    ) <= 0:
        errors.append("minimum_sentence_score must be positive")
    if not isinstance(config.get("abstention_text"), str) or not config.get(
        "abstention_text"
    ):
        errors.append("abstention_text must be non-empty")
    if errors:
        raise ValueError("invalid grounding configuration:\n- " + "\n- ".join(errors))


def injection_matches(text: str, patterns: list[str]) -> list[str]:
    lowered = text.lower()
    return sorted(pattern for pattern in patterns if pattern.lower() in lowered)


def sentence_spans(text: str) -> list[tuple[str, int, int]]:
    spans = []
    for match in SENTENCE.finditer(text):
        start, end = match.span()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            spans.append((text[start:end], start, end))
    return spans


def assemble_context(
    retrieval_result: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    used_words = 0
    seen_sentences: set[str] = set()
    context = []
    blocked = []
    for result in retrieval_result["results"]:
        matches = injection_matches(result["text"], config["injection_patterns"])
        if matches:
            blocked.append(
                {
                    "chunk_id": result["chunk_id"],
                    "document_id": result["document_id"],
                    "reason": "prompt_injection_pattern",
                    "matched_patterns": matches,
                }
            )
            continue
        selected_sentences = []
        for sentence, relative_start, relative_end in sentence_spans(
            result["text"]
        ):
            key = " ".join(tokenize(sentence))
            if key in seen_sentences:
                continue
            words = len(sentence.split())
            if used_words + words > config["context_max_words"]:
                continue
            seen_sentences.add(key)
            selected_sentences.append(
                {
                    "text": sentence,
                    "source_start_char": result["start_char"] + relative_start,
                    "source_end_char": result["start_char"] + relative_end,
                }
            )
            used_words += words
        if not selected_sentences:
            continue
        selected_text = " ".join(item["text"] for item in selected_sentences)
        citation_id = f"S{len(context) + 1}"
        context.append(
            {
                "citation_id": citation_id,
                "chunk_id": result["chunk_id"],
                "document_id": result["document_id"],
                "document_version": result["document_version"],
                "section_id": result["section_id"],
                "title": result["title"],
                "source_uri": result["source_uri"],
                "source_start_char": selected_sentences[0][
                    "source_start_char"
                ],
                "source_end_char": selected_sentences[-1]["source_end_char"],
                "source_spans": selected_sentences,
                "text": selected_text,
                "source_chunk_text_sha256": result["text_sha256"],
                "rank": result["rank"],
                "retrieval_score": result["score"],
                "trust": "untrusted_document_content",
            }
        )
    return {
        "entries": context,
        "blocked": blocked,
        "used_words": used_words,
        "max_words": config["context_max_words"],
    }


def sentence_score(question: str, sentence: str) -> float:
    query_tokens = {token for token in tokenize(question) if token not in STOPWORDS}
    sentence_tokens = set(tokenize(sentence))
    overlap = len(query_tokens & sentence_tokens)
    score = float(overlap)
    lowered_question = question.lower()
    if ("how many" in lowered_question or "how long" in lowered_question or "during which" in lowered_question):
        if sentence_tokens & TIME_WORDS or re.search(r"\b[0-9]{1,2}:[0-9]{2}\b", sentence):
            score += 2.0
    if "what must be validated" in lowered_question and "validate" in sentence_tokens:
        score += 2.0
    if "which endpoint" in lowered_question and "endpoint" in sentence_tokens:
        score += 1.0
    return score


def deterministic_answer(
    question: str, assembled: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    candidates = []
    for entry in assembled["entries"]:
        for source_span in entry["source_spans"]:
            sentence = source_span["text"]
            candidates.append(
                (sentence_score(question, sentence), entry, source_span)
            )
    candidates.sort(
        key=lambda item: (-item[0], item[1]["rank"], item[2]["text"])
    )
    if not candidates or candidates[0][0] < config["minimum_sentence_score"]:
        return {
            "answer": config["abstention_text"],
            "abstained": True,
            "claims": [],
        }
    score, entry, source_span = candidates[0]
    sentence = source_span["text"]
    source_start = source_span["source_start_char"]
    source_end = source_span["source_end_char"]
    claim = {
        "text": sentence,
        "citation_ids": [entry["citation_id"]],
        "source_spans": [
            {
                "citation_id": entry["citation_id"],
                "chunk_id": entry["chunk_id"],
                "document_id": entry["document_id"],
                "document_version": entry["document_version"],
                "source_uri": entry["source_uri"],
                "source_start_char": source_start,
                "source_end_char": source_end,
                "quote": sentence,
            }
        ],
        "extractive_score": score,
    }
    return {
        "answer": f"{sentence} [{entry['citation_id']}]",
        "abstained": False,
        "claims": [claim],
    }


def validate_answer(answer: dict[str, Any]) -> list[str]:
    errors = []
    contexts = {}
    for item in answer.get("context", []):
        citation_id = item.get("citation_id")
        if not isinstance(citation_id, str) or not citation_id:
            errors.append("context entry has no citation_id")
            continue
        if citation_id in contexts:
            errors.append(f"duplicate citation {citation_id}")
            continue
        contexts[citation_id] = item
    if answer.get("abstained") and answer.get("claims"):
        errors.append("abstained answers must not contain claims")
    for claim in answer.get("claims", []):
        citations = claim.get("citation_ids", [])
        if not citations:
            errors.append("claim has no citation")
        for citation_id in citations:
            if citation_id not in contexts:
                errors.append(f"unknown citation {citation_id}")
        for source_span in claim.get("source_spans", []):
            citation_id = source_span.get("citation_id")
            context = contexts.get(citation_id)
            if context is None:
                errors.append(f"unknown citation {citation_id}")
                continue
            if source_span.get("chunk_id") != context.get("chunk_id"):
                errors.append(f"citation {citation_id} points to the wrong chunk")
            for identity_field in (
                "document_id",
                "document_version",
                "source_uri",
            ):
                if source_span.get(identity_field) != context.get(
                    identity_field
                ):
                    errors.append(
                        f"citation {citation_id} has mismatched {identity_field}"
                    )
            quote = source_span.get("quote")
            start = source_span.get("source_start_char")
            end = source_span.get("source_end_char")
            if (
                not isinstance(quote, str)
                or not quote
                or not isinstance(start, int)
                or not isinstance(end, int)
                or end <= start
                or end - start != len(quote)
            ):
                errors.append(
                    f"citation {citation_id} has invalid quote or source offsets"
                )
                continue
            mapped = False
            for context_span in context.get("source_spans", []):
                context_start = context_span.get("source_start_char")
                context_end = context_span.get("source_end_char")
                context_text = context_span.get("text")
                if (
                    not isinstance(context_start, int)
                    or not isinstance(context_end, int)
                    or not isinstance(context_text, str)
                    or start < context_start
                    or end > context_end
                ):
                    continue
                relative_start = start - context_start
                relative_end = end - context_start
                if context_text[relative_start:relative_end] == quote:
                    mapped = True
                    break
            if not mapped:
                errors.append(
                    f"citation {citation_id} quote and offsets do not map to context"
                )
        if set(citations) != {
            item.get("citation_id") for item in claim.get("source_spans", [])
        }:
            errors.append("claim citation_ids and source_spans differ")
    return errors


def validate_question_fixture(
    fixture: dict[str, Any], system: GroundedSystem
) -> None:
    errors = []
    manifest = json.loads(
        (system.retriever.index_dir / "manifest.json").read_text()
    )
    if fixture.get("index_source_sha256") != manifest["source"]["sha256"]:
        errors.append(
            "question fixture index_source_sha256 does not match the active corpus"
        )
    seen = set()
    for question in fixture.get("questions", []):
        question_id = question.get("id")
        if question_id in seen:
            errors.append(f"duplicate question id {question_id!r}")
        seen.add(question_id)
        tenant_id = question.get("tenant_id")
        relevant = question.get("relevant_chunk_ids")
        answerable = question.get("answerable")
        if not isinstance(relevant, list):
            errors.append(
                f"question {question_id}: relevant_chunk_ids must be a list"
            )
            continue
        if answerable is True and not relevant:
            errors.append(
                f"question {question_id}: answerable question needs relevant chunks"
            )
        if answerable is False and relevant:
            errors.append(
                f"question {question_id}: unanswerable question has relevant chunks"
            )
        if not isinstance(answerable, bool):
            errors.append(f"question {question_id}: answerable must be boolean")
        for chunk_id in relevant:
            chunk = system.retriever.chunk_by_id.get(chunk_id)
            if chunk is None:
                errors.append(
                    f"question {question_id}: unknown relevant chunk {chunk_id}"
                )
            elif tenant_id not in chunk["tenant_ids"]:
                errors.append(
                    f"question {question_id}: relevant chunk {chunk_id} "
                    f"is unauthorized for {tenant_id}"
                )
    if errors:
        raise ValueError(
            "invalid question fixture:\n- " + "\n- ".join(errors)
        )


class GroundedSystem:
    def __init__(
        self,
        index_dir: Path,
        retrieval_config: dict[str, Any],
        grounding_config: dict[str, Any],
    ) -> None:
        validate_config(retrieval_config)
        validate_grounding_config(grounding_config)
        self.retriever = Retriever(index_dir, retrieval_config)
        self.config = grounding_config

    def answer(self, question: str, tenant_id: str) -> dict[str, Any]:
        retrieval = self.retriever.retrieve(
            question,
            tenant_id,
            self.config["retrieval_method"],
            self.config["retrieval_top_k"],
        )
        assembled = assemble_context(retrieval, self.config)
        generated = deterministic_answer(question, assembled, self.config)
        report = {
            "schema_version": 1,
            "question": question,
            "tenant_id": tenant_id,
            "retrieval": {
                "method": retrieval["method"],
                "filter_stage": retrieval["filter_stage"],
                "candidate_chunk_ids": [
                    item["chunk_id"] for item in retrieval["results"]
                ],
                "candidate_document_ids": [
                    item["document_id"] for item in retrieval["results"]
                ],
                "elapsed_ns": retrieval["elapsed_ns"],
            },
            "context_budget": {
                "used_words": assembled["used_words"],
                "max_words": assembled["max_words"],
            },
            "blocked_chunks": assembled["blocked"],
            "context": assembled["entries"],
            **generated,
            "generator": {
                "type": "deterministic_extractive_fallback",
                "external_model_used": False,
            },
        }
        errors = validate_answer(report)
        if errors:
            raise ValueError("answer validation failed:\n- " + "\n- ".join(errors))
        return report


def evaluate(
    system: GroundedSystem, questions_path: Path, output: Path
) -> dict[str, Any]:
    fixture = json.loads(questions_path.read_text())
    validate_question_fixture(fixture, system)
    cases = []
    answerable_hits = []
    recalls = []
    phrase_scores = []
    abstention_scores = []
    supported_claims = []
    for question in fixture["questions"]:
        result = system.answer(question["question"], question["tenant_id"])
        returned = set(result["retrieval"]["candidate_chunk_ids"])
        relevant = set(question["relevant_chunk_ids"])
        retrieval_hit = bool(returned & relevant) if relevant else not bool(returned & relevant)
        recall = len(returned & relevant) / len(relevant) if relevant else 1.0
        if question["answerable"]:
            answerable_hits.append(float(bool(returned & relevant)))
            recalls.append(recall)
        answer_lower = result["answer"].lower()
        phrase_passed = all(
            phrase.lower() in answer_lower for phrase in question["expected_phrases"]
        )
        if question["answerable"]:
            phrase_scores.append(float(phrase_passed and not result["abstained"]))
        abstention_correct = result["abstained"] == (not question["answerable"])
        abstention_scores.append(float(abstention_correct))
        claim_support = not validate_answer(result)
        if result["claims"]:
            supported_claims.append(float(claim_support))
        forbidden = set(question.get("forbidden_document_ids", []))
        leaked = sorted(
            forbidden & set(result["retrieval"]["candidate_document_ids"])
        )
        cases.append(
            {
                "question_id": question["id"],
                "answerable": question["answerable"],
                "retrieval_hit": retrieval_hit,
                "retrieval_recall_at_k": recall,
                "expected_phrases_passed": phrase_passed,
                "abstention_correct": abstention_correct,
                "claims_supported": claim_support,
                "leaked_forbidden_document_ids": leaked,
                "result": result,
            }
        )
    report = {
        "schema_version": 1,
        "retrieval_metrics": {
            "answerable_hit_rate": sum(answerable_hits) / max(1, len(answerable_hits)),
            "mean_recall_at_k": sum(recalls) / max(1, len(recalls)),
        },
        "answer_metrics": {
            "expected_phrase_rate": sum(phrase_scores) / max(1, len(phrase_scores)),
            "abstention_accuracy": sum(abstention_scores) / max(1, len(abstention_scores)),
            "supported_claim_rate": sum(supported_claims) / max(1, len(supported_claims)),
        },
        "cases": cases,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def load_system(index: Path, retrieval_config: Path, grounding_config: Path) -> GroundedSystem:
    return GroundedSystem(
        index,
        json.loads(retrieval_config.read_text()),
        json.loads(grounding_config.read_text()),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--retrieval-config", type=Path, required=True)
    parser.add_argument("--grounding-config", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    answer_parser = subparsers.add_parser("answer")
    answer_parser.add_argument("--question", required=True)
    answer_parser.add_argument("--tenant", required=True)
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--questions", type=Path, required=True)
    evaluate_parser.add_argument("--output", type=Path, required=True)
    validate_parser = subparsers.add_parser("validate-answer")
    validate_parser.add_argument("--answer", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        system = load_system(
            args.index, args.retrieval_config, args.grounding_config
        )
        if args.command == "answer":
            print(
                json.dumps(
                    system.answer(args.question, args.tenant),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.command == "evaluate":
            report = evaluate(system, args.questions, args.output)
            print(
                "retrieval hit="
                f"{report['retrieval_metrics']['answerable_hit_rate']:.3f} "
                "answer phrases="
                f"{report['answer_metrics']['expected_phrase_rate']:.3f} "
                "abstention="
                f"{report['answer_metrics']['abstention_accuracy']:.3f}"
            )
        else:
            answer = json.loads(args.answer.read_text())
            errors = validate_answer(answer)
            if errors:
                raise ValueError("answer validation failed:\n- " + "\n- ".join(errors))
            print("PASS: answer citations map to supplied context")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
