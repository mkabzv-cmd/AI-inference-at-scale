#!/usr/bin/env python3
"""Small transparent, OpenAI-shaped Transformers inference server."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from asynccontextlib import asynccontextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import torch
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
)


MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")
MODEL_REVISION = os.environ.get(
    "MODEL_REVISION",
    "7ae557604adf67be50417f59c2c2f167def9a775",
)
MODEL_PATH = os.environ.get("MODEL_PATH", "/models/snapshot")
PROVENANCE_PATH = Path(MODEL_PATH).parent / ".model-provenance.json"
MAX_INPUT_TOKENS = int(os.environ.get("MAX_INPUT_TOKENS", "2048"))
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "256"))
WARMUP = os.environ.get("WARMUP", "true").lower() == "true"

tokenizer = None
model = None
load_state = "starting"
load_error: str | None = None
generation_lock = threading.Lock()
metrics_lock = threading.Lock()
metrics = {
    "requests_total": 0,
    "request_failures_total": 0,
    "prompt_tokens_total": 0,
    "completion_tokens_total": 0,
    "inflight_requests": 0,
}


def log(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


def bytes_on_disk(path: Path) -> int:
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file() and not item.is_symlink()
    )


def validate_model_snapshot() -> dict[str, object]:
    model_path = Path(MODEL_PATH)
    try:
        provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(
            f"missing or invalid model provenance at {PROVENANCE_PATH}"
        ) from exc

    if provenance.get("model_id") != MODEL_ID:
        raise RuntimeError(
            "model provenance ID does not match MODEL_ID: "
            f"{provenance.get('model_id')!r} != {MODEL_ID!r}"
        )
    if provenance.get("revision") != MODEL_REVISION:
        raise RuntimeError(
            "model provenance revision does not match MODEL_REVISION: "
            f"{provenance.get('revision')!r} != {MODEL_REVISION!r}"
        )

    observed_bytes = bytes_on_disk(model_path) if model_path.is_dir() else 0
    if observed_bytes <= 0 or provenance.get("total_bytes") != observed_bytes:
        raise RuntimeError(
            "model snapshot size does not match its completion marker: "
            f"marker={provenance.get('total_bytes')!r}, "
            f"observed={observed_bytes}"
        )
    return provenance


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1, max_length=128)
    max_tokens: int = Field(default=128, ge=1, le=512)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, gt=0.0, le=1.0)
    stream: bool = False


def encode_request(request: ChatCompletionRequest):
    assert tokenizer is not None
    prompt = tokenizer.apply_chat_template(
        [message.model_dump() for message in request.messages],
        tokenize=False,
        add_generation_prompt=True,
    )
    encoded = tokenizer(
        prompt,
        return_tensors="pt",
        add_special_tokens=False,
    )
    prompt_tokens = int(encoded.input_ids.shape[1])
    if prompt_tokens > MAX_INPUT_TOKENS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"prompt has {prompt_tokens} tokens; "
                f"limit is {MAX_INPUT_TOKENS}"
            ),
        )
    return encoded, prompt_tokens


def build_inputs(request: ChatCompletionRequest):
    encoded, prompt_tokens = encode_request(request)
    return encoded.to("cuda"), prompt_tokens


def validate_input_length(request: ChatCompletionRequest) -> None:
    # StreamingResponse sends HTTP headers before iterating its body. Validate
    # prompt length first so an oversized streaming request receives HTTP 400
    # instead of a partial HTTP 200 stream.
    encode_request(request)


def generation_kwargs(
    request: ChatCompletionRequest,
    encoded,
) -> dict[str, object]:
    kwargs: dict[str, object] = {
        **encoded,
        "max_new_tokens": min(request.max_tokens, MAX_NEW_TOKENS),
        "do_sample": request.temperature > 0,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if request.temperature > 0:
        kwargs["temperature"] = request.temperature
        kwargs["top_p"] = request.top_p
    return kwargs


def update_metrics(**deltas: int) -> None:
    with metrics_lock:
        for key, delta in deltas.items():
            metrics[key] += delta


def generate_once(
    request: ChatCompletionRequest,
    *,
    record_metrics: bool = True,
) -> dict[str, object]:
    assert model is not None
    assert tokenizer is not None
    with generation_lock:
        encoded, prompt_tokens = build_inputs(request)
        started = time.monotonic()
        with torch.inference_mode():
            output = model.generate(**generation_kwargs(request, encoded))
        generated = output[0, encoded.input_ids.shape[1] :]
        completion_tokens = int(generated.shape[0])
        text = tokenizer.decode(generated, skip_special_tokens=True)
        if record_metrics:
            update_metrics(
                prompt_tokens_total=prompt_tokens,
                completion_tokens_total=completion_tokens,
            )
        log(
            "generation_finished",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            seconds=round(time.monotonic() - started, 4),
        )
        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }


def stream_events(
    request: ChatCompletionRequest,
    completion_id: str,
    created: int,
) -> Iterator[str]:
    assert model is not None
    assert tokenizer is not None

    try:
        with generation_lock:
            encoded, prompt_tokens = build_inputs(request)
            streamer = TextIteratorStreamer(
                tokenizer,
                skip_prompt=True,
                skip_special_tokens=True,
            )
            kwargs = generation_kwargs(request, encoded)
            kwargs["streamer"] = streamer
            errors: list[Exception] = []
            outputs: list[torch.Tensor] = []

            def run_generation() -> None:
                try:
                    with torch.inference_mode():
                        outputs.append(model.generate(**kwargs))
                except Exception as exc:  # noqa: BLE001 - return an SSE error
                    errors.append(exc)
                    streamer.end()

            thread = threading.Thread(target=run_generation, daemon=True)
            thread.start()
            try:
                first = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": MODEL_ID,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(first)}\n\n"

                for text in streamer:
                    chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": MODEL_ID,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": text},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
            finally:
                # If the client disconnects while CUDA is still generating,
                # keep the lock until that generation thread has actually
                # stopped. Otherwise a second request could use the model
                # concurrently despite this server's serialization promise.
                thread.join()

            if errors:
                raise errors[0]
            if not outputs:
                raise RuntimeError("generation ended without an output tensor")

            completion_tokens = int(
                outputs[0].shape[1] - encoded.input_ids.shape[1]
            )
            update_metrics(
                prompt_tokens_total=prompt_tokens,
                completion_tokens_total=completion_tokens,
            )
            final = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": MODEL_ID,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"
    except GeneratorExit:
        raise
    except Exception as exc:  # response headers have already been sent
        update_metrics(request_failures_total=1)
        log(
            "stream_generation_failed",
            error=type(exc).__name__,
            message=str(exc),
        )
        error_chunk = {
            "error": {
                "type": type(exc).__name__,
                "message": "stream generation failed",
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    finally:
        update_metrics(inflight_requests=-1)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global tokenizer, model, load_state, load_error

    started = time.monotonic()
    try:
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available; verify GPU resource allocation and "
                "the NVIDIA device plugin"
            )
        log(
            "model_load_started",
            model_id=MODEL_ID,
            revision=MODEL_REVISION,
            path=MODEL_PATH,
            gpu=torch.cuda.get_device_name(0),
        )
        provenance = validate_model_snapshot()
        log(
            "model_provenance_verified",
            model_id=provenance["model_id"],
            revision=provenance["revision"],
            total_bytes=provenance["total_bytes"],
        )
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_PATH,
            local_files_only=True,
            trust_remote_code=False,
        )
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float16,
            local_files_only=True,
            trust_remote_code=False,
        ).to("cuda")
        model.eval()

        if WARMUP:
            warmup = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="Say ready.")],
                max_tokens=1,
                temperature=0,
            )
            generate_once(warmup, record_metrics=False)

        load_state = "ready"
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        log(
            "model_ready",
            seconds=round(time.monotonic() - started, 3),
            gpu=torch.cuda.get_device_name(0),
            allocated_mib=round(torch.cuda.memory_allocated() / 1024**2, 1),
            free_mib=round(free_bytes / 1024**2, 1),
            total_mib=round(total_bytes / 1024**2, 1),
        )
    except Exception as exc:
        load_state = "failed"
        load_error = f"{type(exc).__name__}: {exc}"
        log("model_load_failed", error=load_error)
        raise

    yield

    load_state = "stopping"
    model = None
    tokenizer = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    log("server_stopped")


app = FastAPI(
    title="One-GPU teaching API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health/live")
def live() -> dict[str, object]:
    return {"live": True, "state": load_state}


@app.get("/health/ready")
def ready() -> Response:
    status = 200 if load_state == "ready" else 503
    return Response(
        content=json.dumps(
            {
                "ready": load_state == "ready",
                "state": load_state,
                "error": load_error,
            }
        ),
        media_type="application/json",
        status_code=status,
    )


@app.get("/v1/models")
def models() -> dict[str, object]:
    if load_state != "ready":
        raise HTTPException(status_code=503, detail="model is not ready")
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "owned_by": "local",
                "revision": MODEL_REVISION,
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if load_state != "ready":
        raise HTTPException(status_code=503, detail="model is not ready")
    if request.model not in (None, MODEL_ID):
        raise HTTPException(status_code=404, detail="requested model is not loaded")

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    update_metrics(requests_total=1, inflight_requests=1)

    if request.stream:
        try:
            await asyncio.to_thread(validate_input_length, request)
        except HTTPException:
            update_metrics(request_failures_total=1, inflight_requests=-1)
            raise
        except Exception as exc:
            update_metrics(request_failures_total=1, inflight_requests=-1)
            log(
                "stream_validation_failed",
                error=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(
                status_code=500,
                detail="stream request validation failed",
            ) from exc
        return StreamingResponse(
            stream_events(request, completion_id, created),
            media_type="text/event-stream",
        )

    try:
        result = await asyncio.to_thread(generate_once, request)
    except HTTPException:
        update_metrics(request_failures_total=1)
        raise
    except Exception as exc:
        update_metrics(request_failures_total=1)
        log(
            "generation_failed",
            error=type(exc).__name__,
            message=str(exc),
        )
        raise HTTPException(status_code=500, detail="generation failed") from exc

    finally:
        update_metrics(inflight_requests=-1)

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result["text"],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": (
                result["prompt_tokens"] + result["completion_tokens"]
            ),
        },
    }


@app.get("/metrics")
def prometheus_metrics() -> Response:
    with metrics_lock:
        snapshot = dict(metrics)
    lines = [
        "# HELP teaching_api_requests_total Chat completion requests.",
        "# TYPE teaching_api_requests_total counter",
        f"teaching_api_requests_total {snapshot['requests_total']}",
        "# HELP teaching_api_request_failures_total Failed requests.",
        "# TYPE teaching_api_request_failures_total counter",
        (
            "teaching_api_request_failures_total "
            f"{snapshot['request_failures_total']}"
        ),
        "# HELP teaching_api_inflight_requests Current in-flight requests.",
        "# TYPE teaching_api_inflight_requests gauge",
        (
            "teaching_api_inflight_requests "
            f"{snapshot['inflight_requests']}"
        ),
        "# HELP teaching_api_prompt_tokens_total Prompt tokens processed.",
        "# TYPE teaching_api_prompt_tokens_total counter",
        (
            "teaching_api_prompt_tokens_total "
            f"{snapshot['prompt_tokens_total']}"
        ),
        "# HELP teaching_api_completion_tokens_total Tokens generated.",
        "# TYPE teaching_api_completion_tokens_total counter",
        (
            "teaching_api_completion_tokens_total "
            f"{snapshot['completion_tokens_total']}"
        ),
    ]
    if torch.cuda.is_available():
        lines.extend(
            [
                "# HELP teaching_api_gpu_memory_allocated_bytes Torch memory.",
                "# TYPE teaching_api_gpu_memory_allocated_bytes gauge",
                (
                    "teaching_api_gpu_memory_allocated_bytes "
                    f"{torch.cuda.memory_allocated()}"
                ),
                "# HELP teaching_api_gpu_memory_reserved_bytes Torch reserve.",
                "# TYPE teaching_api_gpu_memory_reserved_bytes gauge",
                (
                    "teaching_api_gpu_memory_reserved_bytes "
                    f"{torch.cuda.memory_reserved()}"
                ),
            ]
        )
    return Response(content="\n".join(lines) + "\n", media_type="text/plain")
