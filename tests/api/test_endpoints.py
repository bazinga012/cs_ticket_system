import asyncio
import os
import shutil

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints import router
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.models import User, Ticket, Message, TicketStatus

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
TEST_UPLOAD_DIR = "test_uploads"

app = FastAPI()
app.include_router(router)

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True
)
TestingSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_test_user(session: AsyncSession) -> User:
    stmt = select(User).where(User.email == "test@example.com")
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_test_cs_rep(session: AsyncSession) -> User:
    stmt = select(User).where(User.email == "cs@example.com")
    result = await session.execute(stmt)
    return result.scalar_one()


@pytest.fixture(autouse=True)
async def setup_database():
    if os.path.exists("test.db"):
        os.remove("test.db")
    if os.path.exists(TEST_UPLOAD_DIR):
        shutil.rmtree(TEST_UPLOAD_DIR)

    os.makedirs(TEST_UPLOAD_DIR, exist_ok=True)
    settings.UPLOAD_DIR = TEST_UPLOAD_DIR

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        test_user = User(
            email="test@example.com",
            hashed_password="test_hash",
            is_cs_rep=False
        )
        test_cs_rep = User(
            email="cs@example.com",
            hashed_password="test_hash",
            is_cs_rep=True
        )
        session.add(test_user)
        session.add(test_cs_rep)
        await session.commit()

    yield

    await engine.dispose()
    if os.path.exists("test.db"):
        os.remove("test.db")
    if os.path.exists(TEST_UPLOAD_DIR):
        shutil.rmtree(TEST_UPLOAD_DIR)


@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client_requiring_auth(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return await get_test_user(db_session)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def cs_rep_client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return await get_test_cs_rep(db_session)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_ticket(db_session: AsyncSession):
    user = await get_test_user(db_session)
    ticket = Ticket(
        title="Test Ticket",
        description="Test Description",
        user_id=user.id,
        status=TicketStatus.OPEN
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    return ticket


@pytest.mark.asyncio
async def test_create_ticket(client: AsyncClient):
    response = await client.post(
        "/tickets/",
        data={
            "title": "Test Ticket",
            "description": "Test Description"
        }
    )
    assert response.status_code == 200
    ticket_data = response.json()
    assert ticket_data["title"] == "Test Ticket"
    assert ticket_data["description"] == "Test Description"
    assert ticket_data["status"] == TicketStatus.OPEN.value


@pytest.mark.asyncio
async def test_concurrent_message_creation(
        client: AsyncClient,
        cs_rep_client: AsyncClient,
        test_ticket: Ticket
):
    async def create_message(cl: AsyncClient, content: str):
        return await cl.post(
            f"/tickets/{test_ticket.id}/messages/",
            data={"content": content}
        )

    responses = []
    for i in range(2):
        responses.append(await create_message(client, f"Customer Message {i}"))
        responses.append(await create_message(cs_rep_client, f"CS Rep Message {i}"))

    assert all(r.status_code == 200 for r in responses)

    async with TestingSessionLocal() as session:
        stmt = select(Message).where(Message.ticket_id == test_ticket.id)
        result = await session.execute(stmt)
        messages = result.scalars().all()
        assert len(messages) == 4


@pytest.mark.asyncio
async def test_ticket_lifecycle(
        client: AsyncClient,
        cs_rep_client: AsyncClient,
        test_ticket: Ticket
):
    # CS Rep adds a message
    response = await cs_rep_client.post(
        f"/tickets/{test_ticket.id}/messages/",
        data={"content": "CS Rep response"}
    )
    assert response.status_code == 200

    # Verify IN_PROGRESS status
    response = await client.get(f"/tickets/{test_ticket.id}")
    assert response.json()["status"] == TicketStatus.IN_PROGRESS.value

    # CS Rep closes ticket
    response = await cs_rep_client.patch(f"/tickets/{test_ticket.id}/close")
    assert response.status_code == 200

    # Customer tries to add message to closed ticket
    response = await client.post(
        f"/tickets/{test_ticket.id}/messages/",
        data={"content": "Message to closed ticket"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_error_cases(
        client_requiring_auth: AsyncClient,
        db_session: AsyncSession
):
    # Create a ticket owned by CS rep
    cs_rep = await get_test_cs_rep(db_session)
    cs_rep_ticket = Ticket(
        title="CS Rep Ticket",
        description="CS Rep Description",
        user_id=cs_rep.id,
        status=TicketStatus.OPEN
    )
    db_session.add(cs_rep_ticket)
    await db_session.commit()
    await db_session.refresh(cs_rep_ticket)

    # Regular user tries to access CS rep's ticket
    response = await client_requiring_auth.get(f"/tickets/{cs_rep_ticket.id}")
    assert response.status_code == 401

    # Regular user creates their own ticket
    user_ticket = Ticket(
        title="User Ticket",
        description="User Description",
        user_id=(await get_test_user(db_session)).id,
        status=TicketStatus.OPEN
    )
    db_session.add(user_ticket)
    await db_session.commit()
    await db_session.refresh(user_ticket)

    # Regular user tries to close their ticket (should fail)
    response = await client_requiring_auth.patch(f"/tickets/{user_ticket.id}/close")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_attachment_operations(
        client: AsyncClient,
        test_ticket: Ticket,
        db_session: AsyncSession
):
    # Create test file
    test_file_content = b"test content"
    test_file_path = os.path.join(TEST_UPLOAD_DIR, "test_file.txt")
    with open(test_file_path, "wb") as f:
        f.write(test_file_content)

    # Create message with attachment
    files = [
        ("attachments", ("test_file.txt", open(test_file_path, "rb"), "text/plain"))
    ]
    data = {"content": "Message with attachment"}

    response = await client.post(
        f"/tickets/{test_ticket.id}/messages/",
        data=data,
        files=files
    )
    assert response.status_code == 200

    message_data = response.json()
    assert len(message_data["attachments"]) > 0
    attachment = message_data["attachments"][0]

    # Verify file exists
    assert os.path.exists(attachment["file_path"])

    # Delete attachment
    response = await client.delete(
        f"/messages/{message_data['id']}/attachments/{attachment['id']}"
    )
    assert response.status_code == 200

    # Wait briefly for file deletion
    await asyncio.sleep(0.1)

    # Verify file was deleted
    assert not os.path.exists(attachment["file_path"])
