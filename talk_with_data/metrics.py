from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from random import Random
from statistics import mean, stdev
from typing import Literal, get_args

Outcome = Literal["correct", "wrong", "empty", "error"]

OUTCOMES: tuple[Outcome, ...] = get_args(Outcome)
RESAMPLES = 1000
CONFIDENCE = 0.95
DECIMALS = 3
SEED = 42


@dataclass(frozen=True)
class Attempt:
    question_id: str
    template: str
    run: int
    question: str
    sql: str
    outcome: Outcome
    result: object
    gold: object


def summarize(attempts: Sequence[Attempt]) -> dict[str, object]:
    template_accuracies = _compute_template_accuracies(attempts)
    lower, upper = _bootstrap_interval(list(template_accuracies.values()), Random(SEED))
    rates = _compute_outcome_rates(attempts)

    return {
        "questions": len({attempt.question_id for attempt in attempts}),
        "runs": len({attempt.run for attempt in attempts}),
        "accuracy": round(_compute_accuracy(attempts), DECIMALS),
        "accuracy_std": round(_compute_accuracy_std(attempts), DECIMALS),
        "accuracy_ci95": [round(lower, DECIMALS), round(upper, DECIMALS)],
        "outcomes": {outcome: round(rate, DECIMALS) for outcome, rate in rates.items()},
        "consistency": _count_consistency(attempts),
        "template_accuracy": {
            template: round(accuracy, DECIMALS)
            for template, accuracy in template_accuracies.items()
        },
    }


def _compute_accuracy(attempts: Sequence[Attempt]) -> float:
    return sum(attempt.outcome == "correct" for attempt in attempts) / len(attempts)


def _compute_accuracy_std(attempts: Sequence[Attempt]) -> float:
    return stdev(_compute_run_accuracies(attempts))


def _compute_run_accuracies(attempts: Sequence[Attempt]) -> list[float]:
    runs = _group_by(attempts, lambda attempt: attempt.run)

    return [_compute_accuracy(runs[run]) for run in sorted(runs)]


def _compute_outcome_rates(attempts: Sequence[Attempt]) -> dict[Outcome, float]:
    counts = Counter(attempt.outcome for attempt in attempts)

    return {outcome: counts[outcome] / len(attempts) for outcome in OUTCOMES}


def _compute_template_accuracies(attempts: Sequence[Attempt]) -> dict[str, float]:
    templates = _group_by(attempts, lambda attempt: attempt.template)

    return {template: _compute_accuracy(group) for template, group in templates.items()}


def _count_consistency(attempts: Sequence[Attempt]) -> dict[str, int]:
    questions = _group_by(attempts, lambda attempt: attempt.question_id)
    accuracies = [_compute_accuracy(group) for group in questions.values()]

    return {
        "always_correct": sum(accuracy == 1 for accuracy in accuracies),
        "sometimes_correct": sum(0 < accuracy < 1 for accuracy in accuracies),
        "never_correct": sum(accuracy == 0 for accuracy in accuracies),
    }


def _bootstrap_interval(values: Sequence[float], rng: Random) -> tuple[float, float]:
    means = sorted(mean(rng.choices(values, k=len(values))) for _ in range(RESAMPLES))
    tail = (1 - CONFIDENCE) / 2

    return means[int(RESAMPLES * tail)], means[int(RESAMPLES * (1 - tail)) - 1]


def _group_by[Key](
    attempts: Sequence[Attempt], key: Callable[[Attempt], Key]
) -> dict[Key, list[Attempt]]:
    groups: dict[Key, list[Attempt]] = {}

    for attempt in attempts:
        groups.setdefault(key(attempt), []).append(attempt)

    return groups
