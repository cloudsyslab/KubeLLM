import unittest
from types import SimpleNamespace

from phi.model.message import Message

from debug_assistant_latest.responses_model import OpenAIResponsesChat


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class OpenAIResponsesModelTests(unittest.TestCase):
    def invoke_with_fake_client(self, model, endpoint, messages):
        object.__setattr__(model, "client", SimpleNamespace(responses=endpoint))
        return model.invoke(messages)

    def make_response(self, output, *, status="completed", incomplete_details=None):
        return SimpleNamespace(
            id="resp_test",
            created_at=1_800_000_000,
            model="gpt-6.2-sol",
            status=status,
            incomplete_details=incomplete_details,
            output=output,
            usage=SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15),
        )

    def test_invocation_flattens_tools_and_converts_function_call(self):
        endpoint = FakeResponses(
            self.make_response(
                [
                    SimpleNamespace(
                        type="function_call",
                        call_id="call_1",
                        name="inspect_pod",
                        arguments='{"namespace":"default"}',
                    )
                ]
            )
        )
        model = OpenAIResponsesChat(
            id="gpt-6.2-sol",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "inspect_pod",
                        "description": "Inspect a pod",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        )
        result = self.invoke_with_fake_client(
            model,
            endpoint,
            [Message(role="system", content="Inspect safely."), Message(role="user", content="Check pod.")]
        )

        self.assertEqual(
            endpoint.calls[0]["input"],
            [
                {"role": "system", "content": "Inspect safely."},
                {"role": "user", "content": "Check pod."},
            ],
        )
        self.assertEqual(
            endpoint.calls[0]["tools"],
            [
                {
                    "type": "function",
                    "name": "inspect_pod",
                    "description": "Inspect a pod",
                    "parameters": {"type": "object", "properties": {}},
                }
            ],
        )
        tool_call = result.choices[0].message.tool_calls[0]
        self.assertEqual((tool_call.id, tool_call.function.name), ("call_1", "inspect_pod"))
        self.assertEqual(result.usage.prompt_tokens, 10)

    def test_incomplete_text_response_is_not_a_normal_completion(self):
        endpoint = FakeResponses(
            self.make_response(
                [SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text="partial")])],
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
            )
        )
        model = OpenAIResponsesChat(id="gpt-6.2-sol")

        with self.assertRaisesRegex(RuntimeError, r"status=incomplete.*max_output_tokens"):
            self.invoke_with_fake_client(model, endpoint, [Message(role="user", content="Repair this.")])

    def test_failed_or_unreported_status_cannot_yield_tool_calls(self):
        tool_output = [
            SimpleNamespace(type="function_call", call_id="call_partial", name="inspect_pod", arguments="{}")
        ]
        for status, expected in (("failed", "failed"), (None, "missing")):
            with self.subTest(status=status):
                endpoint = FakeResponses(self.make_response(tool_output, status=status))
                model = OpenAIResponsesChat(id="gpt-6.2-sol")
                with self.assertRaisesRegex(RuntimeError, f"status={expected}"):
                    self.invoke_with_fake_client(model, endpoint, [Message(role="user", content="Inspect.")])

    def test_followup_maps_assistant_calls_and_tool_results(self):
        endpoint = FakeResponses(self.make_response([]))
        model = OpenAIResponsesChat(id="gpt-6.2-sol")
        self.invoke_with_fake_client(
            model,
            endpoint,
            [
                Message(
                    role="assistant",
                    tool_calls=[
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "inspect_pod", "arguments": '{"namespace":"default"}'},
                        }
                    ],
                ),
                Message(role="tool", tool_call_id="call_1", content="pod is ready"),
            ]
        )

        self.assertEqual(
            endpoint.calls[0]["input"],
            [
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "inspect_pod",
                    "arguments": '{"namespace":"default"}',
                },
                {"type": "function_call_output", "call_id": "call_1", "output": "pod is ready"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
