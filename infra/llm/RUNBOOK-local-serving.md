# Local LLM serving — RTX 6000 Pro Blackwell (96 GB) via vLLM

Hybrid setup: this project routes every call through the LiteLLM proxy (`config.yaml`).
Cloud models are live now; the **local half flips on** when you set `LOCAL_LLM_BASE` to
the vLLM endpoint. Serving stack = **vLLM** (your choice), behind Traefik.

## Hard reality of one 96 GB card

A single RTX 6000 Pro Blackwell (GB202, sm_120, 96 GB GDDR7) holds **ONE large MoE at a
time**. The 2026 headline coders (GLM-4.6/5.1, Qwen3-Coder-480B, Kimi K2, DeepSeek V4-Pro)
do **NOT** fit one card — they need ~4×. What fits one card at usable quant:

| Class | Model | Quant / fit | Role | vLLM serve name |
|-------|-------|-------------|------|-----------------|
| thinking/coding | GLM-4.5-Air (106B-A12B) | AWQ-4bit (~60-65 GB) | `local-thinking` | `local-thinking` |
| thinking (fast alt) | Qwen3-Coder-Next (80B-A3B) | FP8 (~47 GB, 256K ctx) | `local-thinking` | `local-thinking` |
| vision | Qwen3-VL-30B/32B | AWQ/FP8 (~24-30 GB) | `local-vision` | `local-vision` |
| embedding | Qwen3-Embedding / BGE-class | FP8 (small) | `local-embed` | `local-embed` |

**thinking and vision ALTERNATE** (model-swap) — they cannot co-reside at full context.
The embedding model is small and can run alongside one large model. Use FP8 KV cache to
buy ~128-200K context on the big MoE.

## vLLM serving (OpenAI-compatible /v1)

Blackwell sm_120 notes: use **FP8/AWQ** (the NVFP4 path still crashes as of mid-2026),
`--gpu-memory-utilization 0.9`, `tensor_parallel_size=1`, FP8 KV cache, and the model's
tool-call + reasoning parsers so agentic tool loops work.

```bash
# thinking/coding (serve as model name "local-thinking")
vllm serve cpatonn/GLM-4.5-Air-AWQ-4bit \
  --served-model-name local-thinking \
  --quantization awq --kv-cache-dtype fp8 \
  --gpu-memory-utilization 0.9 --max-model-len 131072 \
  --enable-auto-tool-choice --tool-call-parser glm45 --reasoning-parser glm45 \
  --port 8000

# vision (swap-in; serve as "local-vision")
vllm serve Qwen/Qwen3-VL-32B-Instruct-AWQ \
  --served-model-name local-vision --quantization awq \
  --gpu-memory-utilization 0.9 --max-model-len 65536 \
  --limit-mm-per-prompt image=8 --port 8000

# embedding (serve as "local-embed")
vllm serve Qwen/Qwen3-Embedding-0.6B --task embed \
  --served-model-name local-embed --port 8001
```

## Wire into LiteLLM (already configured)

`config.yaml` already defines `local-thinking` / `local-vision` / `local-embed` pointing at
`api_base: os.environ/LOCAL_LLM_BASE`, cost 0, with cloud fallbacks. To activate:

```bash
# in the LiteLLM proxy's environment (.env behind Traefik)
LOCAL_LLM_BASE=http://<gpu-host-or-traefik>/v1   # e.g. http://vllm.<slug>.localhost/v1
LOCAL_LLM_KEY=<any-non-empty-token>              # vLLM accepts --api-key
```

`allowed_fails: 2` + `cooldown_time: 60` park a cold/swapping endpoint so a model swap
never blocks the agent fleet; the role/`local-*` fallback chains route to cloud meanwhile.
Pin **LiteLLM ≥ 1.83.0** (mid-2026 supply-chain advisory).

## Routing recap (engineering-core:model-routing)

- Local-first for high-volume roles (`role-backend-codegen`, `role-bulk-worker`, `role-qa-gate`).
- Cloud reasoning tier for `role-architect` / `role-debugger` / `role-reviewer`.
- Vision (`role-frontend-vision`) → Gemini cloud or `local-vision` swap-in.
- Reviewer ≠ author enforced via `review-of-<family>` chains.
