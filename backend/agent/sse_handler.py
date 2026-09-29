import json
import asyncio
import re
from typing import Dict, Any, List, Optional, AsyncGenerator

class SSEHandler:
    """
    Handles Server-Sent Events (SSE) formatting, token streaming, and client stream parsing.
    Decouples streaming transport from agent reasoning logic.
    """

    @staticmethod
    def format_event(event_type: str, payload: Dict[str, Any]) -> str:
        """Formats a typed event into an SSE standard data packet."""
        data = {"type": event_type, **payload}
        return f"data: {json.dumps(data, default=str)}\n\n"

    @staticmethod
    def format_guard(tripwire: Optional[str], latency_ms: float, provider: Optional[str], intent: str = "ANALYTICAL") -> str:
        """Emits System 1 safety guard status."""
        return SSEHandler.format_event("guard", {
            "tripwire": tripwire,
            "intent": intent,
            "latency_ms": round(latency_ms, 2),
            "provider": provider
        })

    @staticmethod
    def format_tool_call(tool_name: str, args: Any = None) -> str:
        """Emits a live tool invocation event when querying database."""
        return SSEHandler.format_event("tool_call", {"tool": tool_name, "args": args or {}})

    @staticmethod
    def format_tool_result(tool_name: str, result: Any = None) -> str:
        """Emits a live tool result event when database returns telemetry."""
        return SSEHandler.format_event("tool_result", {"tool": tool_name, "result": result or {}})

    @staticmethod
    def format_token(content: str) -> str:
        """Emits a single text token delta."""
        return SSEHandler.format_event("token", {"content": content})

    @staticmethod
    def format_done(
        response: str,
        tool_calls: List[Dict[str, Any]],
        latency_ms: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
        system1_latency_ms: float = 0.0,
        guard_tripwire: Optional[str] = None,
        provider: Optional[str] = None,
        framework: str = "PydanticAI",
        model_name: Optional[str] = None
    ) -> str:
        """Emits the final completed payload with tool call inspections and usage metadata."""
        return SSEHandler.format_event("done", {
            "response": response,
            "tool_calls": tool_calls,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": round(latency_ms, 2),
            "system1_latency_ms": round(system1_latency_ms, 2),
            "guard_tripwire": guard_tripwire,
            "system_one_provider": provider,
            "framework": framework,
            "model_name": model_name
        })

    @staticmethod
    def format_done_marker() -> str:
        """Emits the standard SSE terminal marker."""
        return "data: [DONE]\n\n"

    @staticmethod
    async def stream_text_tokens(text: str, delay: float = 0.005) -> AsyncGenerator[str, None]:
        """Splits full text into token/word chunks and yields SSE token events with natural cadence."""
        tokens = re.split(r'(\s+)', text)
        for t in tokens:
            if t:
                yield SSEHandler.format_token(t)
                if delay > 0:
                    await asyncio.sleep(delay)

    @staticmethod
    async def parse_stream(stream_gen: AsyncGenerator[str, None]) -> Dict[str, Any]:
        """
        Helper for evaluation harness and REST endpoints:
        Consumes an SSE async generator and reconstructs the full response dict.
        """
        result = {
            "response": "",
            "tool_calls": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0.0,
            "system1_latency_ms": 0.0,
            "guard_tripwire": None,
            "system_one_provider": None
        }
        accumulated_tokens = []
        async for chunk in stream_gen:
            for line in chunk.split("\n"):
                line = line.strip()
                if not line.startswith("data: "):
                    continue
                payload_str = line[6:].strip()
                if payload_str == "[DONE]":
                    break
                try:
                    evt = json.loads(payload_str)
                    etype = evt.get("type")
                    if etype == "token":
                        accumulated_tokens.append(evt.get("content", ""))
                    elif etype == "done":
                        result.update({
                            "response": evt.get("response", "".join(accumulated_tokens)),
                            "tool_calls": evt.get("tool_calls", []),
                            "tokens_in": evt.get("tokens_in", 0),
                            "tokens_out": evt.get("tokens_out", 0),
                            "latency_ms": evt.get("latency_ms", 0.0),
                            "system1_latency_ms": evt.get("system1_latency_ms", 0.0),
                            "guard_tripwire": evt.get("guard_tripwire"),
                            "system_one_provider": evt.get("system_one_provider"),
                            "model_name": evt.get("model_name")
                        })
                except Exception:
                    pass

        if not result["response"] and accumulated_tokens:
            result["response"] = "".join(accumulated_tokens)
        return result
