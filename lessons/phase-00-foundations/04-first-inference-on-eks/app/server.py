#!/usr/bin/env python3
"""Tiny educational NDJSON model server; deliberately not a serving engine."""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = None
TOKENIZER = None
DEVICE = None
READY = False
LOAD_ERROR = None
GENERATION_LOCK = threading.Lock()
REQUEST_COUNT = 0
GENERATED_TOKEN_COUNT = 0


def boolean_env(name, default):
    value = os.environ.get(name, str(default)).lower()
    if value not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return value == "true"


def write_json(handler, status, payload):
    body = (json.dumps(payload) + "\n").encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def filtered_logits(logits, temperature, top_p):
    scaled = logits / temperature
    if top_p >= 1.0:
        return scaled
    sorted_logits, sorted_indices = torch.sort(scaled, descending=True)
    cumulative = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
    remove = cumulative > top_p
    remove[..., 1:] = remove[..., :-1].clone()
    remove[..., 0] = False
    original_order_remove = torch.zeros_like(remove).scatter(
        1, sorted_indices, remove
    )
    return scaled.masked_fill(original_order_remove, float("-inf"))


class Handler(BaseHTTPRequestHandler):
    server_version = "lesson04/1"

    def log_message(self, format_string, *args):
        print(
            json.dumps(
                {
                    "kind": "access",
                    "client": self.client_address[0],
                    "message": format_string % args,
                }
            ),
            flush=True,
        )

    def do_GET(self):
        if self.path == "/healthz":
            write_json(self, 200, {"alive": True})
            return
        if self.path == "/readyz":
            status = 200 if READY else 503
            write_json(
                self,
                status,
                {"ready": READY, "load_error": LOAD_ERROR if not READY else None},
            )
            return
        if self.path == "/info":
            gpu_name = None
            allocated = None
            if DEVICE is not None and DEVICE.type == "cuda":
                gpu_name = torch.cuda.get_device_name(DEVICE)
                allocated = torch.cuda.memory_allocated(DEVICE)
            write_json(
                self,
                200 if READY else 503,
                {
                    "ready": READY,
                    "model_id": os.environ.get("MODEL_ID"),
                    "model_revision": os.environ.get("MODEL_REVISION"),
                    "device": str(DEVICE) if DEVICE is not None else None,
                    "cuda_available": torch.cuda.is_available(),
                    "gpu_name": gpu_name,
                    "gpu_memory_allocated_bytes": allocated,
                    "torch_version": torch.__version__,
                    "torch_cuda_build": torch.version.cuda,
                    "request_count": REQUEST_COUNT,
                    "generated_token_count": GENERATED_TOKEN_COUNT,
                },
            )
            return
        write_json(self, 404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/generate":
            write_json(self, 404, {"error": "not found"})
            return
        if not READY:
            write_json(self, 503, {"error": "model not ready"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 64 * 1024:
                raise ValueError("Content-Length must be between 1 and 65536")
            request = json.loads(self.rfile.read(length))
            prompt = request["prompt"]
            max_new_tokens = int(request.get("max_new_tokens", 12))
            temperature = float(request.get("temperature", 0.0))
            top_p = float(request.get("top_p", 1.0))
            seed = int(request.get("seed", 42))
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("prompt must be a non-empty string")
            if not 1 <= max_new_tokens <= 64:
                raise ValueError("max_new_tokens must be in [1, 64]")
            if temperature < 0:
                raise ValueError("temperature cannot be negative")
            if not 0 < top_p <= 1:
                raise ValueError("top_p must be in (0, 1]")
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
            write_json(self, 400, {"error": str(error)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        try:
            with GENERATION_LOCK:
                self.stream_generation(
                    prompt, max_new_tokens, temperature, top_p, seed
                )
        except (BrokenPipeError, ConnectionResetError):
            print('{"kind":"client-disconnected"}', flush=True)
        except Exception as error:
            event = {
                "event": "error",
                "type": type(error).__name__,
                "message": str(error),
            }
            self.wfile.write((json.dumps(event) + "\n").encode("utf-8"))
            self.wfile.flush()

    def stream_generation(
        self, prompt, max_new_tokens, temperature, top_p, seed
    ):
        global REQUEST_COUNT, GENERATED_TOKEN_COUNT

        encoded = TOKENIZER(prompt, return_tensors="pt")
        input_ids = encoded["input_ids"].to(DEVICE)
        attention_mask = encoded["attention_mask"].to(DEVICE)
        generator = torch.Generator(device=DEVICE).manual_seed(seed)
        generated = []
        past_key_values = None
        current_input = input_ids
        started = time.perf_counter()
        first_token_ms = None
        finish_reason = "length"

        with torch.inference_mode():
            for index in range(max_new_tokens):
                outputs = MODEL(
                    input_ids=current_input,
                    attention_mask=attention_mask,
                    past_key_values=past_key_values,
                    use_cache=True,
                )
                logits = outputs.logits[:, -1, :]
                if temperature == 0:
                    next_token = torch.argmax(logits, dim=-1, keepdim=True)
                else:
                    probabilities = torch.softmax(
                        filtered_logits(logits, temperature, top_p), dim=-1
                    )
                    next_token = torch.multinomial(
                        probabilities, 1, generator=generator
                    )
                token_id = int(next_token.item())
                generated.append(token_id)
                if DEVICE.type == "cuda":
                    torch.cuda.synchronize(DEVICE)
                elapsed_ms = (time.perf_counter() - started) * 1000
                if first_token_ms is None:
                    first_token_ms = elapsed_ms
                event = {
                    "event": "token",
                    "index": index,
                    "token_id": token_id,
                    "text": TOKENIZER.decode(
                        [token_id],
                        clean_up_tokenization_spaces=False,
                        skip_special_tokens=False,
                    ),
                    "elapsed_ms": elapsed_ms,
                }
                self.wfile.write((json.dumps(event) + "\n").encode("utf-8"))
                self.wfile.flush()
                if token_id == TOKENIZER.eos_token_id:
                    finish_reason = "eos"
                    break
                past_key_values = outputs.past_key_values
                current_input = next_token
                attention_mask = torch.cat(
                    [
                        attention_mask,
                        torch.ones(
                            (1, 1),
                            dtype=attention_mask.dtype,
                            device=DEVICE,
                        ),
                    ],
                    dim=1,
                )

        total_ms = (time.perf_counter() - started) * 1000
        REQUEST_COUNT += 1
        GENERATED_TOKEN_COUNT += len(generated)
        complete = {
            "event": "complete",
            "tokens": len(generated),
            "finish_reason": finish_reason,
            "generated_text": TOKENIZER.decode(
                generated, skip_special_tokens=True
            ),
            "first_token_ms": first_token_ms,
            "total_ms": total_ms,
        }
        self.wfile.write((json.dumps(complete) + "\n").encode("utf-8"))
        self.wfile.flush()


def load_model():
    global MODEL, TOKENIZER, DEVICE, READY, LOAD_ERROR

    model_path = os.environ.get("MODEL_PATH", "/opt/model")
    require_cuda = boolean_env("REQUIRE_CUDA", True)
    try:
        if require_cuda and not torch.cuda.is_available():
            raise RuntimeError(
                "REQUIRE_CUDA=true but torch.cuda.is_available() is false"
            )
        DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.float16 if DEVICE.type == "cuda" else torch.float32
        print(f"loading model from {model_path} on {DEVICE}", flush=True)
        TOKENIZER = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
            trust_remote_code=False,
        )
        if TOKENIZER.pad_token_id is None:
            TOKENIZER.pad_token_id = TOKENIZER.eos_token_id
        MODEL = AutoModelForCausalLM.from_pretrained(
            model_path,
            local_files_only=True,
            torch_dtype=dtype,
            trust_remote_code=False,
        ).to(DEVICE)
        MODEL.eval()
        with torch.inference_mode():
            smoke = TOKENIZER("GPU readiness", return_tensors="pt")
            MODEL(smoke["input_ids"].to(DEVICE), use_cache=True)
        if DEVICE.type == "cuda":
            torch.cuda.synchronize(DEVICE)
            print(f"CUDA device: {torch.cuda.get_device_name(DEVICE)}", flush=True)
            print(
                f"allocated VRAM: {torch.cuda.memory_allocated(DEVICE)} bytes",
                flush=True,
            )
        READY = True
        print("model load complete; readiness enabled", flush=True)
    except Exception as error:
        LOAD_ERROR = f"{type(error).__name__}: {error}"
        print(f"model load failed: {LOAD_ERROR}", flush=True)
        raise


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    loader = threading.Thread(target=load_model, name="model-loader", daemon=True)
    print(f"server listening on 0.0.0.0:{port}; model loading", flush=True)
    loader.start()
    server.serve_forever()
