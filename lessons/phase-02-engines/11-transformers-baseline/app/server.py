"""Readable, deliberately non-optimized Transformers inference server.

This server is a teaching reference, not a production serving stack. It exposes
an intentionally small OpenAI-style API while keeping tokenization, prefill,
decode, cache use, sampling, streaming, cancellation, and serialization visible.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import queue
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator

import torch
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, model_validator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    StoppingCriteria,
    StoppingCriteriaList,
    TextIteratorStreamer,
)


MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")
MODEL_REVISION = os.environ.get(
    "MODEL_REVISION", "7ae557604adf67be50417f59c2c2f167def9a775"
)
MODEL_PATH = os.environ.get("MODEL_PATH", MODEL_ID)
DTYPE_NAME = os.environ.get("DTYPE", "float16")
MAX_MODEL_LEN = int(os.environ.get("MAX_MODEL_LEN", "4096"))
SERIALIZE_GENERATION = os.environ.get("SERIALIZE_GENERATION", "true").lower() == "true"

REQUESTS = Counter(
    "transformers_baseline_requests_total",
    "Completed HTTP generation requests",
    ["status", "stream"],
)
INFLIGHT = Gauge(
    "transformers_baseline_inflight_requests",
    "Requests admitted to generation",
)
E2E = Histogram(
    "transformers_baseline_e2e_seconds",
    "End-to-end server generation time",
)
QUEUE_WAIT = Histogram(
    "transformers_baseline_queue_wait_seconds",
    "Time waiting for the single generation lock",
)
TOKENS = Counter(
    "transformers_baseline_generated_tokens_total",
    "Generated tokens reported by the model",
)


class Message(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1, max_length=16_000)


class ChatRequest(BaseModel):
    model: str = MODEL_ID
    messages: list[Message] = Field(min_length=1)
    max_tokens: int = Field(default=64, ge=1, le=512)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    seed: int | None = 42
    stream: bool = False

    @model_validator(mode="after")
    def model_must_match(self) -> "ChatRequest":
        if self.model not in {MODEL_ID, "course-model"}:
            raise ValueError(f"this server only exposes {MODEL_ID!r} and 'course-model'")
        return self


class DisconnectCriteria(StoppingCriteria):
    """Ask generate() to stop after the next decode iteration."""

    def __init__(self, event: threading.Event) -> None:
        self.event = event

    def __call__(
        self,
        input_ids: torch.LongTensor,
        scores: torch.FloatTensor,
        **kwargs: Any,
    ) -> bool:
        del input_ids, scores, kwargs
        return self.event.is_set()


@dataclass
class Runtime:
    tokenizer: Any
    model: Any
    device: str
    dtype: str
    generation_lock: asyncio.Lock
    loaded_at: float


runtime: Runtime | None = None


def dtype_from_name(name: str) -> torch.dtype:
    mapping = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }
    if name not in mapping:
        raise RuntimeError(f"unsupported DTYPE={name}; choose one of {sorted(mapping)}")
    return mapping[name]


def load_runtime() -> Runtime:
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is unavailable. This GPU track intentionally fails instead of "
            "silently running the model on CPU."
        )
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH,
        revision=MODEL_REVISION if MODEL_PATH == MODEL_ID else None,
        trust_remote_code=False,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        revision=MODEL_REVISION if MODEL_PATH == MODEL_ID else None,
        dtype=dtype_from_name(DTYPE_NAME),
        low_cpu_mem_usage=True,
        trust_remote_code=False,
    ).to("cuda:0")
    model.eval()
    return Runtime(
        tokenizer=tokenizer,
        model=model,
        device=torch.cuda.get_device_name(0),
        dtype=str(next(model.parameters()).dtype),
        generation_lock=asyncio.Lock(),
        loaded_at=time.time(),
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global runtime
    runtime = await asyncio.to_thread(load_runtime)
    yield
    runtime = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(title="Transparent Transformers baseline", lifespan=lifespan)


def require_runtime() -> Runtime:
    if runtime is None:
        raise HTTPException(status_code=503, detail="model is not loaded")
    return runtime


def prompt_and_inputs(rt: Runtime, body: ChatRequest) -> tuple[str, dict[str, torch.Tensor]]:
    messages = [message.model_dump() for message in body.messages]
    prompt = rt.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    encoded = rt.tokenizer(
        prompt,
        return_tensors="pt",
        add_special_tokens=False,
        truncation=True,
        max_length=MAX_MODEL_LEN - body.max_tokens,
    )
    return prompt, {key: value.to("cuda:0") for key, value in encoded.items()}


def generation_kwargs(
    body: ChatRequest,
    inputs: dict[str, torch.Tensor],
    cancel: threading.Event,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        **inputs,
        "max_new_tokens": body.max_tokens,
        "use_cache": True,
        "stopping_criteria": StoppingCriteriaList([DisconnectCriteria(cancel)]),
        "pad_token_id": require_runtime().tokenizer.eos_token_id,
    }
    if body.temperature == 0.0:
        kwargs["do_sample"] = False
    else:
        kwargs.update(
            do_sample=True,
            temperature=body.temperature,
            top_p=body.top_p,
        )
        if body.seed is not None:
            torch.manual_seed(body.seed)
            torch.cuda.manual_seed_all(body.seed)
    return kwargs


async def acquire_generation_lock(rt: Runtime) -> tuple[float, bool]:
    started = time.perf_counter()
    acquired = False
    if SERIALIZE_GENERATION:
        await rt.generation_lock.acquire()
        acquired = True
    waited = time.perf_counter() - started
    QUEUE_WAIT.observe(waited)
    return waited, acquired


def release_generation_lock(rt: Runtime, acquired: bool) -> None:
    if acquired:
        rt.generation_lock.release()


def usage(rt: Runtime, input_count: int, output_count: int) -> dict[str, int]:
    del rt
    return {
        "prompt_tokens": input_count,
        "completion_tokens": output_count,
        "total_tokens": input_count + output_count,
    }


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready")
def ready() -> dict[str, Any]:
    rt = require_runtime()
    return {
        "status": "ready",
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "device": rt.device,
        "dtype": rt.dtype,
    }


@app.get("/v1/models")
def models() -> dict[str, Any]:
    require_runtime()
    return {
        "object": "list",
        "data": [
            {
                "id": "course-model",
                "object": "model",
                "owned_by": "course",
                "source": MODEL_ID,
                "revision": MODEL_REVISION,
            }
        ],
    }


@app.get("/debug/runtime")
def debug_runtime() -> dict[str, Any]:
    rt = require_runtime()
    allocated = torch.cuda.memory_allocated(0)
    reserved = torch.cuda.memory_reserved(0)
    return {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "device": rt.device,
        "dtype": rt.dtype,
        "serialized": SERIALIZE_GENERATION,
        "max_model_len": MAX_MODEL_LEN,
        "cuda_memory": {
            "allocated_bytes": allocated,
            "reserved_bytes": reserved,
            "allocator_slack_bytes": reserved - allocated,
        },
        "loaded_at_unix": rt.loaded_at,
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/chat/completions")
async def chat(body: ChatRequest, request: Request) -> Response:
    if body.stream:
        return StreamingResponse(
            stream_completion(body, request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return await non_stream_completion(body, request)


async def non_stream_completion(body: ChatRequest, request: Request) -> JSONResponse:
    rt = require_runtime()
    request_id = f"chatcmpl-{uuid.uuid4().hex}"
    started = time.perf_counter()
    cancel = threading.Event()
    INFLIGHT.inc()
    lock_acquired = False
    try:
        waited, lock_acquired = await acquire_generation_lock(rt)
        if await request.is_disconnected():
            cancel.set()
            raise HTTPException(status_code=499, detail="client disconnected")
        prompt, inputs = prompt_and_inputs(rt, body)
        input_count = int(inputs["input_ids"].shape[-1])
        if input_count + body.max_tokens > MAX_MODEL_LEN:
            raise HTTPException(status_code=400, detail="prompt plus output exceeds context")
        with torch.inference_mode():
            output = await asyncio.to_thread(
                rt.model.generate,
                **generation_kwargs(body, inputs, cancel),
            )
        generated_ids = output[0, input_count:]
        output_count = int(generated_ids.numel())
        text = rt.tokenizer.decode(generated_ids, skip_special_tokens=True)
        elapsed = time.perf_counter() - started
        REQUESTS.labels(status="ok", stream="false").inc()
        E2E.observe(elapsed)
        TOKENS.inc(output_count)
        trace = {
            "queue_wait_ms": round(waited * 1000, 3),
            "e2e_ms": round(elapsed * 1000, 3),
            "input_shape": list(inputs["input_ids"].shape),
            "output_shape": list(output.shape),
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        return JSONResponse(
            {
                "id": request_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "course-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": usage(rt, input_count, output_count),
                "teaching_trace": trace,
            }
        )
    except HTTPException:
        REQUESTS.labels(status="client_error", stream="false").inc()
        raise
    except Exception:
        REQUESTS.labels(status="error", stream="false").inc()
        raise
    finally:
        release_generation_lock(rt, lock_acquired)
        INFLIGHT.dec()


def next_stream_item(iterator: Iterator[str]) -> tuple[str, str]:
    try:
        return "item", next(iterator)
    except StopIteration:
        return "finished", ""
    except queue.Empty:
        return "timeout", ""


async def stream_completion(body: ChatRequest, request: Request) -> AsyncIterator[str]:
    rt = require_runtime()
    request_id = f"chatcmpl-{uuid.uuid4().hex}"
    started = time.perf_counter()
    cancel = threading.Event()
    generation_error: list[BaseException] = []
    INFLIGHT.inc()
    lock_acquired = False
    thread: threading.Thread | None = None
    try:
        _, lock_acquired = await acquire_generation_lock(rt)
        _, inputs = prompt_and_inputs(rt, body)
        input_count = int(inputs["input_ids"].shape[-1])
        streamer = TextIteratorStreamer(
            rt.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            timeout=0.25,
        )
        kwargs = generation_kwargs(body, inputs, cancel)
        kwargs["streamer"] = streamer

        def generate() -> None:
            try:
                with torch.inference_mode():
                    rt.model.generate(**kwargs)
            except BaseException as error:  # forwarded into the SSE stream
                generation_error.append(error)

        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
        iterator = iter(streamer)
        chunk_index = 0
        generated_text = ""
        while True:
            if await request.is_disconnected():
                cancel.set()
                break
            state, text = await asyncio.to_thread(next_stream_item, iterator)
            if state == "finished":
                break
            if state == "timeout":
                if not thread.is_alive():
                    if generation_error:
                        raise generation_error[0]
                    break
                continue
            if text:
                generated_text += text
                payload = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "course-model",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": text},
                            "finish_reason": None,
                        }
                    ],
                    "teaching_chunk_index": chunk_index,
                }
                chunk_index += 1
                yield f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
        await asyncio.to_thread(thread.join)
        if generation_error:
            raise generation_error[0]
        if not cancel.is_set():
            final = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "course-model",
                "choices": [
                    {"index": 0, "delta": {}, "finish_reason": "stop"}
                ],
                "teaching_text_sha256": hashlib.sha256(
                    generated_text.encode()
                ).hexdigest(),
            }
            yield f"data: {json.dumps(final, separators=(',', ':'))}\n\n"
            yield "data: [DONE]\n\n"
            REQUESTS.labels(status="ok", stream="true").inc()
            TOKENS.inc(max(0, len(rt.tokenizer.encode(generated_text, add_special_tokens=False))))
        else:
            REQUESTS.labels(status="cancelled", stream="true").inc()
        E2E.observe(time.perf_counter() - started)
    except Exception as error:
        REQUESTS.labels(status="error", stream="true").inc()
        payload = {"error": {"message": str(error), "type": type(error).__name__}}
        yield f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    finally:
        cancel.set()
        if thread is not None and thread.is_alive():
            await asyncio.to_thread(thread.join)
        release_generation_lock(rt, lock_acquired)
        INFLIGHT.dec()
