"""
공통 로직: 기사 본문 추출 + Claude 판단

judge.py(단일)와 judge_batch.py(여러 개)가 이 모듈을 같이 사용합니다.
판단 기준 자체는 criteria.md 에 있고, 여기서는 그 기준을 불러와 API에 넘기는 역할만 합니다.
"""

import json
from pathlib import Path

import requests
import trafilatura
from bs4 import BeautifulSoup
from anthropic import Anthropic

BASE_DIR = Path(__file__).parent
CRITERIA_PATH = BASE_DIR / "criteria.md"
MODEL = "claude-sonnet-5"  # 속도/비용 우선이면 "claude-haiku-4-5-20251001" 로 교체

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_article(url: str) -> dict:
    """URL에서 기사 제목/매체명/본문을 추출한다."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"페이지를 가져오지 못했습니다: {e}")

    text = trafilatura.extract(html, url=url, include_comments=False)
    metadata = trafilatura.extract_metadata(html, default_url=url)

    title = metadata.title if metadata and metadata.title else None
    site = metadata.sitename if metadata and metadata.sitename else None

    # trafilatura가 본문을 못 뽑으면 <p> 태그만 긁는 단순 fallback
    if not text:
        soup = BeautifulSoup(html, "html.parser")
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        text = "\n".join(p for p in paragraphs if len(p) > 20)
        if not title and soup.title:
            title = soup.title.get_text(strip=True)

    if not text:
        raise RuntimeError(
            "본문을 추출하지 못했습니다. 로그인/구독이 필요하거나 "
            "자바스크립트 렌더링 방식의 사이트일 수 있습니다."
        )

    return {
        "url": url,
        "title": title or "(제목 추출 실패)",
        "site": site or "(매체 추출 실패)",
        "text": text[:6000],  # 토큰 절약용 컷
    }


def load_criteria() -> str:
    if not CRITERIA_PATH.exists():
        raise FileNotFoundError(f"{CRITERIA_PATH} 파일이 없습니다.")
    return CRITERIA_PATH.read_text(encoding="utf-8")


def judge(article: dict, criteria: str, client: Anthropic = None) -> dict:
    """기사 하나에 대해 수집(O)/제외(X)를 판단한다."""
    client = client or Anthropic()

    system_prompt = f"""당신은 중소벤처기업부(중기부) 온라인 모니터링 담당자를 보조하는 판단 보조원입니다.
아래 기준에 따라 주어진 기사를 모니터링 대상으로 수집(O)할지 제외(X)할지 판단하세요.

{criteria}

# 출력 형식
반드시 아래 JSON 형식으로만 답하세요. 다른 설명이나 코드펜스는 붙이지 마세요.
{{"decision": "O 또는 X", "reason": "1~2문장 판단 근거", "topic": "기사의 핵심 주제 한 줄 요약"}}
"""

    user_prompt = f"""매체: {article['site']}
제목: {article['title']}

본문:
{article['text']}
"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = resp.content[0].text.strip()
    raw = raw.strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"decision": "?", "reason": f"응답 파싱 실패, 원문: {raw}", "topic": ""}
