#!/usr/bin/env python3
"""
중기부 온라인 모니터링 - 기사 수집 여부(O/X) 자동 판단 스크립트 (단일 링크용)

여러 링크를 한 번에 처리하려면 judge_batch.py 를 쓰세요.

사용법:
    python judge.py "https://example.com/news/123"

설정:
    같은 폴더에 .env 파일을 만들고 아래처럼 API 키를 넣어두세요.
        ANTHROPIC_API_KEY=sk-ant-...

판단 기준은 criteria.md 에 있습니다. 담당자 피드백이 바뀌면 그 파일만 수정하면 됩니다.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from common import fetch_article, judge, load_criteria

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="기사 URL을 넣으면 중기부 모니터링 수집 여부(O/X)를 판단합니다."
    )
    parser.add_argument("url", help="판단할 기사 URL")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY 가 설정되어 있지 않습니다.\n"
            "이 폴더에 .env 파일을 만들고 ANTHROPIC_API_KEY=sk-ant-... 를 넣어주세요."
        )

    try:
        article = fetch_article(args.url)
    except RuntimeError as e:
        sys.exit(f"[오류] {e}")

    criteria = load_criteria()
    result = judge(article, criteria)

    decision = result.get("decision", "?")
    label = {"O": "⭕ 수집", "X": "❌ 제외"}.get(decision, "❓ 확인 필요")

    print("=" * 50)
    print(f"매체 : {article['site']}")
    print(f"제목 : {article['title']}")
    print("-" * 50)
    print(f"판단 : {label}")
    print(f"주제 : {result.get('topic', '')}")
    print(f"근거 : {result.get('reason', '')}")
    print("=" * 50)


if __name__ == "__main__":
    main()
