"""HTTP API for the web UI.

Endpoints:
    GET  /api/health          liveness check
    GET  /api/criteria        current criteria.md content
    PUT  /api/criteria        overwrite criteria.md
    POST /api/judge           judge a single URL, returns one result
    POST /api/judge/batch     judge many URLs, streams results via SSE
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from anthropic import Anthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import MAX_WORKERS
from .criteria import load_criteria, save_criteria
from .pipeline import process_one
from .schemas import BatchJudgeRequest, CriteriaUpdateRequest, SingleJudgeRequest

app = FastAPI(title="Article Judge AI")

# Local dev tool, no auth: the frontend may be opened as a plain file or
# served from a different port than the API, so allow any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/criteria")
def get_criteria() -> dict:
    return {"content": load_criteria()}


@app.put("/api/criteria")
def update_criteria(payload: CriteriaUpdateRequest) -> dict:
    save_criteria(payload.content)
    return {"status": "saved"}


@app.post("/api/judge")
def judge_single(payload: SingleJudgeRequest) -> dict:
    criteria = load_criteria()
    result = process_one(0, payload.url, criteria, Anthropic())
    return result.to_dict()


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.post("/api/judge/batch")
def judge_batch(payload: BatchJudgeRequest) -> StreamingResponse:
    urls = payload.urls

    def stream():
        yield _sse({"type": "start", "total": len(urls)})

        if not urls:
            yield _sse({"type": "done"})
            return

        criteria = load_criteria()
        client = Anthropic()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(process_one, i, url, criteria, client): i
                for i, url in enumerate(urls)
            }
            for future in as_completed(futures):
                result = future.result()
                yield _sse({"type": "result", "data": result.to_dict()})

        yield _sse({"type": "done"})

    # StreamingResponse runs this generator in FastAPI's threadpool since
    # it's a sync function, so the blocking ThreadPoolExecutor work below
    # doesn't block the event loop.
    return StreamingResponse(stream(), media_type="text/event-stream")
