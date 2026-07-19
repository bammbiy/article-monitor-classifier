"""One failing link must never take down a whole batch — process_one()
always returns a JudgeResult, never raises."""

from article_judge.models import JudgeResult
from article_judge.pipeline import process_one


def test_process_one_returns_error_result_for_unreachable_url():
    result = process_one(
        0, "https://this-domain-does-not-exist-xyz123.example/article", criteria="", client=None
    )
    assert isinstance(result, JudgeResult)
    assert result.decision == "ERROR"
    assert result.error != ""


def test_process_one_numbers_results_from_one():
    result = process_one(4, "https://this-domain-does-not-exist-xyz123.example/x", criteria="", client=None)
    assert result.no == 5
