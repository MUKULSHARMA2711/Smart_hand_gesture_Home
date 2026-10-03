"""Claude provider. The only module that imports the Anthropic SDK.

Runs a manual tool loop where Claude may call the *read-only* tools, then returns a
plan constrained to PLAN_SCHEMA via structured outputs. Claude never receives a tool
that changes devices; the plan it returns is validated by the backend before execution.
"""

import json
import logging
from typing import Any

from app.ai.prompts import PLAN_SCHEMA, SYSTEM_PROMPT, normalize_llm_plan, render_user_prompt
from app.ai.providers.base import AIProvider, AIProviderError, PlanningRequest
from app.ai.tools import READ_ONLY_TOOL_SPECS, ToolError

logger = logging.getLogger(__name__)

# Server-side refusal fallback: if a safety classifier declines, the API retries on the
# model Anthropic recommends for that refusal category.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        effort: str = "medium",
        max_tool_rounds: int = 4,
        timeout_s: float = 60.0,
        client: Any = None,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise AIProviderError("The 'anthropic' package is not installed: pip install anthropic") from exc

        self._sdk = anthropic
        self.model = model
        self._effort = effort
        self._max_tool_rounds = max_tool_rounds
        # Without an explicit key the SDK resolves ANTHROPIC_API_KEY / an `ant auth login` profile.
        try:
            self._client = client or (
                anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout_s)
                if api_key
                else anthropic.AsyncAnthropic(timeout=timeout_s)
            )
        except anthropic.AnthropicError as exc:
            raise AIProviderError(f"The AI provider is not configured correctly: {exc}") from exc
        self._tools = [{**spec, "strict": True} for spec in READ_ONLY_TOOL_SPECS]

    async def plan(self, request: PlanningRequest) -> dict[str, Any]:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": render_user_prompt(request.message, request.context)}
        ]

        for _ in range(self._max_tool_rounds + 1):
            response = await self._create(messages)

            if response.stop_reason == "refusal":
                category = getattr(getattr(response, "stop_details", None), "category", None)
                raise AIProviderError(f"The model declined this request (category: {category}).")
            if response.stop_reason == "max_tokens":
                raise AIProviderError("The model's response was cut off before the plan was complete.")

            if response.stop_reason == "tool_use":
                # Keep the assistant turn intact (including thinking blocks) and answer every tool call.
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": self._run_tools(request, response.content)})
                continue

            text = "".join(block.text for block in response.content if block.type == "text")
            try:
                plan = json.loads(text)
            except json.JSONDecodeError as exc:
                raise AIProviderError("The model did not return valid JSON.") from exc
            if not isinstance(plan, dict):
                raise AIProviderError("The model's plan was not a JSON object.")
            return normalize_llm_plan(plan)

        raise AIProviderError(f"The model used more than {self._max_tool_rounds} rounds of tool calls.")

    async def _create(self, messages: list[dict[str, Any]]) -> Any:
        sdk = self._sdk
        try:
            return await self._client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=self._tools,
                messages=messages,
                output_config={
                    "effort": self._effort,
                    "format": {"type": "json_schema", "schema": PLAN_SCHEMA},
                },
                betas=[_FALLBACK_BETA],
                fallbacks="default",
            )
        except sdk.AuthenticationError as exc:
            raise AIProviderError("AI provider authentication failed. Check SMARTHOME_AI_API_KEY / ANTHROPIC_API_KEY.") from exc
        except sdk.RateLimitError as exc:
            raise AIProviderError("The AI provider is rate limiting requests. Try again shortly.") from exc
        except sdk.APIStatusError as exc:
            raise AIProviderError(f"The AI provider returned an error ({exc.status_code}).") from exc
        except sdk.APIConnectionError as exc:
            raise AIProviderError("Could not reach the AI provider.") from exc
        except sdk.AnthropicError as exc:  # e.g. no credentials configured
            raise AIProviderError(f"The AI provider is not configured correctly: {exc}") from exc

    @staticmethod
    def _run_tools(request: PlanningRequest, content: list[Any]) -> list[dict[str, Any]]:
        results = []
        for block in content:
            if block.type != "tool_use":
                continue
            try:
                output = request.tools.call_read_only(block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output)})
            except ToolError as exc:
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(exc), "is_error": True})
        return results
