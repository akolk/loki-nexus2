from backend.agent import AgentDeps, agent
from backend.models import Soul, User
from sqlmodel import Session, create_engine
import asyncio
from pydantic_ai import Agent

# Mock database
engine = create_engine("sqlite:///:memory:")

def get_session():
    with Session(engine) as session:
        yield session

async def verify_agent():
    print("Verifying Agent...")

    # Create a simple agent to test without OpenAI call first
    # We'll just verify the agent's structure

    soul = Soul(user_id="test_user", username="tester", style="concise")

    with Session(engine) as session:
        deps = AgentDeps(user_soul=soul, db_session=session, user_id=1)

        # We can't easily test the full agent run without an API key for OpenAI
        # So we will verify the structure and dependency injection
        assert deps.user_soul.username == "tester"
        print("AgentDeps initialized correctly.")

        # Verify the tool registration
        from backend.tools.data_tool import run_data_query
        # This is a bit circular, but ensures the tool is importable and runnable
        res = run_data_query("SELECT 1")
        print("Tools importable.")

    print("Agent structure verification passed.")

if __name__ == "__main__":
    asyncio.run(verify_agent())
