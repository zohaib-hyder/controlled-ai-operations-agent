> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Optional provider-neutral LLM planner

Default `AI_PROVIDER=mock` requires no key, network or paid service. The planner interface accepts typed bounded context and returns one typed decision; the optional `OpenAICompatiblePlanner` uses a fixed Chat Completions endpoint. It does not execute provider-native tool calls. All proposed invocations return to the same deterministic backend validators and ToolExecutor.

Explicit opt-in configuration (in ignored `.env`, never committed):

```dotenv
AI_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=<your-key>
LLM_MODEL=<your-compatible-model>
LLM_TIMEOUT_SECONDS=2
LLM_MAX_OUTPUT_TOKENS=1024
LLM_MAX_REQUESTS=8
LLM_TOTAL_OUTPUT_TOKENS=8192
LLM_MAX_COST_MICROUSD=100000
LLM_INPUT_USD_PER_MILLION=<positive-configured-input-rate>
LLM_OUTPUT_USD_PER_MILLION=<positive-configured-output-rate>
PLANNER_CONTEXT_BYTES=65536
```

Rates above are deliberately unspecified: select your provider/model and confirm its rates yourself. No model/pricing recommendation or live account verification is implied. An explicitly selected provider with missing endpoint/key/model/rates is rejected; absent opt-in remains mock. Provider errors never silently fall back. Restart/recreate the backend after changing configuration. HTTPS is required; credentials in URL, query and fragment are prohibited. The agent cannot select a URL, headers, model or rate. Redirect following, proxy environment and retries are disabled. Keys are secret settings, excluded from representation and not included in context, checkpoints, hashes, traces or logs. HTTP client debug/request logging is suppressed.

Protocol: POST the configured base plus `/chat/completions`, fixed model/messages, `response_format={"type":"json_object"}`, and `max_completion_tokens`. JSON mode alone is not a schema guarantee: the backend parses through the strict discriminated Pydantic decision adapter, rejects extra/executable fields, malformed JSON, refusal, truncation and provider-native tool calls, then independently authorizes any invocation. The wire fields were checked against [official OpenAI documentation](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create). Other compatible providers may implement different subsets; compatibility is not assumed to have been live tested.

Time is bounded by both provider timeout and remaining investigation wall time. Streamed response bytes are capped at 32 KiB and decision content at 16 KiB; transport/body/parse failures become safe reason codes with no raw provider error. Context is minimized and bounded, with untrusted-data instructions and a six-tool read allowlist. That prompt is supplementary; deterministic scope/schema/RBAC checks provide the boundary.

Before each provider call, persist one request, the maximum output-token reservation and a conservative configured-cost reservation. Input reservation uses UTF-8 byte length of context/system/schema plus a fixed framing allowance; output uses configured max tokens. Cost is rounded up in micro-USD using configured per-million-token rates. Requests, token reservations and cost reservations never reset on recovery and are not refunded after failure. These are admission limits based on configured rates/tokenizer assumptions, not billing measurements or a guarantee about an arbitrary vendor's metering. Trace/UI explicitly label reservations. No paid calls occur during tests or verification.

Recovery binds nonsecret provider configuration with SHA256 (endpoint, model, timeout, output cap, rates, context cap), while original durable Limits remain authoritative. Key rotation does not change this hash; a changed execution configuration stops instead of disguising a new provider as continuation of an old one. A crash after a charged planning reservation consumes it; a new request, if needed, is separately charged. Completed enterprise tools are not replayed.

Verification status: injected HTTPX MockTransport tests exercise accepted wire output, HTTP failure, redirect rejection, timeout, oversized/refused/malformed output, budget gates and no fallback. Real paid provider behavior is **unverified**. No API key or paid access was requested for this phase.
