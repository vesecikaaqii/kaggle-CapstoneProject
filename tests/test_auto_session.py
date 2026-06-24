import asyncio
from google.adk import Agent, Runner
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.models.registry import LLMRegistry
from google.genai import types

class MockLlm(BaseLlm):
    @classmethod
    def supported_models(cls) -> list[str]:
        return ["mock-model"]
    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False):
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="Auto Session Ok")]
            )
        )

LLMRegistry.register(MockLlm)

def main():
    agent = Agent(name="a", model="mock-model")
    runner = Runner(agent=agent, app_name="app")
    msg = types.Content(role="user", parts=[types.Part.from_text(text="hi")])
    for event in runner.run(user_id="u", session_id="s", new_message=msg):
        print("Event:", event.content.parts[0].text if event.content else "Event")

if __name__ == "__main__":
    main()
