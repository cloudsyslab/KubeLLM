"""Responses API bridge for Phi's existing OpenAI function-tool loop."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from openai.types.completion_usage import CompletionUsage
from phi.model.message import Message
from phi.model.openai.chat import OpenAIChat


def _value(item: Any, name: str, default=None):
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, default=str)


class OpenAIResponsesChat(OpenAIChat):
    """Keep Phi 2.7's tool execution while sending GPT-6 requests to Responses."""

    def _responses_input(self, messages: List[Message]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for message in messages:
            if message.images or message.audio or message.videos:
                raise ValueError("The GPT-6 Responses adapter currently supports text-only KubeLLM messages.")
            if message.role == "tool":
                if not message.tool_call_id:
                    raise ValueError("A tool result is missing its tool_call_id.")
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.tool_call_id,
                        "output": _text(message.content),
                    }
                )
                continue
            if message.role == "assistant" and message.tool_calls:
                if message.content:
                    items.append({"role": "assistant", "content": _text(message.content)})
                for call in message.tool_calls:
                    function = call.get("function") or {}
                    call_id = call.get("id")
                    name = function.get("name")
                    arguments = function.get("arguments", "{}")
                    if not call_id or not name:
                        raise ValueError("An assistant tool call is missing its id or function name.")
                    items.append(
                        {
                            "type": "function_call",
                            "call_id": call_id,
                            "name": name,
                            "arguments": arguments if isinstance(arguments, str) else _text(arguments),
                        }
                    )
                continue
            role = "system" if message.role == "system" else message.role
            if role not in {"system", "developer", "user", "assistant"}:
                raise ValueError(f"Unsupported Responses input role: {message.role}")
            if message.content is not None:
                items.append({"role": role, "content": _text(message.content)})
        return items

    def _responses_tools(self) -> Optional[List[Dict[str, Any]]]:
        tools = self.get_tools_for_api()
        if not tools:
            return None
        formatted: List[Dict[str, Any]] = []
        for tool in tools:
            if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
                formatted.append({"type": "function", **tool["function"]})
            else:
                formatted.append(tool)
        return formatted

    def _responses_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.store is not None:
            kwargs["store"] = self.store
        if self.metadata is not None:
            kwargs["metadata"] = self.metadata
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        output_limit = self.max_completion_tokens or self.max_tokens
        if output_limit is not None:
            kwargs["max_output_tokens"] = output_limit
        tools = self._responses_tools()
        if tools is not None:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = self.tool_choice or "auto"
        custom = dict(self.request_params or {})
        extra_body = custom.pop("extra_body", None)
        if isinstance(extra_body, dict):
            custom.update(extra_body)
        effort = custom.pop("reasoning_effort", None)
        if effort is not None:
            kwargs["reasoning"] = {"effort": effort}
        kwargs.update(custom)
        return kwargs

    def _as_chat_completion(self, response: Any) -> ChatCompletion:
        content_parts: List[str] = []
        refusal_parts: List[str] = []
        tool_calls: List[ChatCompletionMessageToolCall] = []
        for item in _value(response, "output", []) or []:
            item_type = _value(item, "type")
            if item_type == "function_call":
                tool_calls.append(
                    ChatCompletionMessageToolCall(
                        id=_value(item, "call_id"),
                        type="function",
                        function={
                            "name": _value(item, "name"),
                            "arguments": _value(item, "arguments", "{}"),
                        },
                    )
                )
            elif item_type == "message":
                for part in _value(item, "content", []) or []:
                    part_type = _value(part, "type")
                    if part_type == "output_text":
                        content_parts.append(_value(part, "text", ""))
                    elif part_type == "refusal":
                        refusal_parts.append(_value(part, "refusal", ""))
        message = ChatCompletionMessage(
            role="assistant",
            content="".join(content_parts) or None,
            refusal="".join(refusal_parts) or None,
            tool_calls=tool_calls or None,
        )
        source_usage = _value(response, "usage")
        usage = None
        if source_usage is not None:
            input_tokens = _value(source_usage, "input_tokens") or 0
            output_tokens = _value(source_usage, "output_tokens") or 0
            usage = CompletionUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=_value(source_usage, "total_tokens", input_tokens + output_tokens),
            )
        return ChatCompletion(
            id=_value(response, "id", ""),
            choices=[
                Choice(
                    finish_reason="tool_calls" if tool_calls else "stop",
                    index=0,
                    message=message,
                )
            ],
            created=int(_value(response, "created_at") or time.time()),
            model=_value(response, "model", self.id),
            object="chat.completion",
            usage=usage,
        )

    def invoke(self, messages: List[Message]) -> ChatCompletion:
        response = self.get_client().responses.create(
            model=self.id,
            input=self._responses_input(messages),
            **self._responses_kwargs(),
        )
        return self._as_chat_completion(response)

    async def ainvoke(self, messages: List[Message]) -> ChatCompletion:
        response = await self.get_async_client().responses.create(
            model=self.id,
            input=self._responses_input(messages),
            **self._responses_kwargs(),
        )
        return self._as_chat_completion(response)

    def invoke_stream(self, messages: List[Message]):
        raise NotImplementedError("The KubeLLM GPT-6 Responses adapter is non-streaming.")

    async def ainvoke_stream(self, messages: List[Message]):
        raise NotImplementedError("The KubeLLM GPT-6 Responses adapter is non-streaming.")
