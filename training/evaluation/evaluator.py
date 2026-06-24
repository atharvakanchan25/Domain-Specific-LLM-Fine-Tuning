"""
Module 9: Evaluation Framework
Metrics: BLEU, ROUGE, F1, Hallucination Rate, Groundedness, Answer Relevance
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import nltk
nltk.download("punkt", quiet=True)


@dataclass
class EvalResult:
    bleu: float
    rouge1: float
    rouge2: float
    rougeL: float
    exact_match: float
    answer_relevance: float
    hallucination_rate: float
    sample_count: int


class Evaluator:
    def __init__(self):
        self.rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        self.smooth = SmoothingFunction().method1

    def evaluate_file(self, predictions_file: Path) -> EvalResult:
        """
        predictions_file: JSONL with {question, ground_truth, prediction, context}
        """
        records = [json.loads(l) for l in predictions_file.read_text().splitlines() if l.strip()]
        return self.evaluate(records)

    def evaluate(self, records: list[dict]) -> EvalResult:
        bleu_scores, r1, r2, rL, em = [], [], [], [], []
        for rec in records:
            pred = rec.get("prediction", "")
            ref = rec.get("ground_truth", "")
            bleu_scores.append(
                sentence_bleu([ref.split()], pred.split(), smoothing_function=self.smooth)
            )
            scores = self.rouge.score(ref, pred)
            r1.append(scores["rouge1"].fmeasure)
            r2.append(scores["rouge2"].fmeasure)
            rL.append(scores["rougeL"].fmeasure)
            em.append(float(pred.strip() == ref.strip()))

        return EvalResult(
            bleu=round(sum(bleu_scores) / len(bleu_scores), 4),
            rouge1=round(sum(r1) / len(r1), 4),
            rouge2=round(sum(r2) / len(r2), 4),
            rougeL=round(sum(rL) / len(rL), 4),
            exact_match=round(sum(em) / len(em), 4),
            answer_relevance=0.0,    # TODO: implement with LLM-as-judge
            hallucination_rate=0.0,  # TODO: implement NLI-based check
            sample_count=len(records),
        )

    def save_report(self, result: EvalResult, output_path: Path) -> None:
        output_path.write_text(json.dumps(asdict(result), indent=2))
        print(f"Evaluation report saved to {output_path}")


if __name__ == "__main__":
    import sys
    ev = Evaluator()
    result = ev.evaluate_file(Path(sys.argv[1]))
    print(json.dumps(asdict(result), indent=2))
