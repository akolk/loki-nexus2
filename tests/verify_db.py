from backend.database import init_db, engine
from backend.models import User, ResearchStep, ChatHistory
from sqlmodel import Session

def verify_db_setup():
    print("Initializing database...")
    init_db()
    print("Database initialized.")

    with Session(engine) as session:
        # Create a test user
        test_user = User(username="test_researcher", soul_data={"style": "technical"})
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        print(f"Created user: {test_user}")

        # Create a test research step
        step = ResearchStep(
            user_id=test_user.id,
            query="Analyze data",
            thought_process="I should check the data distribution.",
            output_summary="Data is skewed.",
            output_metadata={"rows": 100}
        )
        session.add(step)
        session.commit()
        session.refresh(step)
        print(f"Created research step: {step}")

        # Create a chat history entry
        chat = ChatHistory(
            user_id=test_user.id,
            role="user",
            content="Hello"
        )
        session.add(chat)
        session.commit()
        session.refresh(chat)
        print(f"Created chat history: {chat}")

    print("Verification complete.")

if __name__ == "__main__":
    verify_db_setup()
