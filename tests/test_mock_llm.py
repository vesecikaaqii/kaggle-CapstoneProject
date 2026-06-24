import asyncio
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.models.registry import LLMRegistry
from google.genai import types

class MockLlm(BaseLlm):
    @classmethod
    def supported_models(cls) -> list[str]:
        return ["mock-model"]

    async def generate_content(self, llm_request: LlmRequest, stream: bool = False):
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="Hello from Mock LLM!")]
            )
        )

# Register the mock provider
LLMRegistry.register(MockLlm)

async def test_run():
    agent = Agent(
        name="test_agent",
        model="mock-model",
        instruction="Test"
    )
    runner = Runner(
        agent=agent,
        app_name="test_app",
        session_service=InMemorySessionService()
    )
    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Hi")]
    )
    events = runner.run(user_id="u1", session_id="s1", new_message=user_message)
    for event in events:
        print("Event:", event)

if __name__ == "__main__":
    asyncio.run(test_run())
