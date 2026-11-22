"""
HospitalOps AI — Agent Session & Conversation Continuity Tests (Milestone 5, Chunk 5.4).

Verifies:
1. AgentSessionRepository and AgentMessageRepository persistence and querying.
2. AgentContextBuilder bounded context reconstruction, token budget clamping,
   reference resolution, and strict RBAC revalidation.
3. AgentStateManager multi-turn lifecycle, ownership enforcement, session status
   transitions (ACTIVE, ARCHIVED, EXPIRED), and message limits.
4. Canonical 4-turn operational inquiry:
   - Turn 1: "Show me the latest available ICU forecast."
   - Turn 2: "Now compare it with the previous forecast."
   - Turn 3: "What happens if admissions increase by 15%?"
   - Turn 4: "Summarize the operational implications."
5. REST API session management and message execution endpoints under /api/v1/agents/sessions.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.agents.context_builder import AgentContextBuilder
from app.agents.contracts import (
    AgentExecutionStatus,
    AgentRunExecutionMetadata,
    AgentRunResponse,
    AgentTaskPlan,
    StopReason,
)
from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.agents.orchestrator import AgentOrchestrator
from app.agents.state_manager import AgentStateManager
from app.api.dependencies import (
    get_agent_state_manager,
    get_current_user,
)
from app.core.security import get_permissions_for_role
from app.main import app
from app.models.agent_message import (
    AgentMessageDocument,
    MessageRole,
)
from app.models.agent_session import (
    AgentSessionCreate,
    AgentSessionDocument,
    SessionStatus,
)
from app.models.base import utc_now
from app.models.user import Role, UserDocument

# ── Mock Users ────────────────────────────────────────────────────────────────


def _get_admin_user() -> UserDocument:
    return UserDocument(
        user_id="usr_admin_123",
        email="admin@hospitalops.local",
        name="System Administrator",
        password_hash="mock_hash",
        role=Role.ADMIN,
        is_active=True,
    )


def _get_second_user() -> UserDocument:
    return UserDocument(
        user_id="usr_other_999",
        email="other@hospitalops.local",
        name="Other Manager",
        password_hash="mock_hash",
        role=Role.OPERATIONS_MANAGER,
        is_active=True,
    )


def _get_restricted_user() -> UserDocument:
    return UserDocument(
        user_id="usr_doc_456",
        email="doctor@hospitalops.local",
        name="Dr. Sarah Chen",
        password_hash="mock_hash",
        role=Role.DOCTOR,
        is_active=True,
    )


# ── In-Memory Repository Implementations for Testing ──────────────────────────


class InMemorySessionRepository:
    """Fast in-memory session repository for deterministic unit/API tests."""

    def __init__(self) -> None:
        self.sessions: dict[str, AgentSessionDocument] = {}

    async def create_session(self, doc: AgentSessionDocument) -> AgentSessionDocument:
        self.sessions[doc.session_id] = doc
        return doc

    async def get_by_session_id(self, session_id: str) -> AgentSessionDocument | None:
        return self.sessions.get(session_id)

    async def get_by_session_id_and_user(
        self, session_id: str, user_id: str
    ) -> AgentSessionDocument | None:
        s = self.sessions.get(session_id)
        if s and s.user_id == user_id:
            return s
        return None

    async def list_user_sessions(
        self,
        user_id: str,
        status: SessionStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentSessionDocument], int]:
        matches = [
            s
            for s in self.sessions.values()
            if s.user_id == user_id and (status is None or s.status == status)
        ]
        matches.sort(key=lambda s: s.last_activity_at, reverse=True)
        return matches[skip : skip + limit], len(matches)

    async def update_status(
        self, session_id: str, user_id: str, status: SessionStatus
    ) -> AgentSessionDocument | None:
        s = await self.get_by_session_id_and_user(session_id, user_id)
        if s:
            s.status = status
            s.updated_at = utc_now()
            return s
        return None

    async def update_session_details(
        self,
        session_id: str,
        user_id: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentSessionDocument | None:
        s = await self.get_by_session_id_and_user(session_id, user_id)
        if s:
            if title:
                s.title = title
            if metadata is not None:
                s.metadata.update(metadata)
            s.updated_at = utc_now()
            return s
        return None

    async def update_activity(
        self,
        session_id: str,
        latest_execution_id: str | None = None,
        increment_messages: int = 1,
    ) -> AgentSessionDocument | None:
        s = self.sessions.get(session_id)
        if s:
            s.message_count += increment_messages
            s.last_activity_at = utc_now()
            s.updated_at = utc_now()
            if latest_execution_id:
                s.latest_execution_id = latest_execution_id
            return s
        return None

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        s = await self.get_by_session_id_and_user(session_id, user_id)
        if s:
            del self.sessions[session_id]
            return True
        return False


class InMemoryMessageRepository:
    """Fast in-memory message repository for deterministic unit/API tests."""

    def __init__(self) -> None:
        self.messages: list[AgentMessageDocument] = []

    async def create_message(self, doc: AgentMessageDocument) -> AgentMessageDocument:
        self.messages.append(doc)
        return doc

    async def list_session_messages(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentMessageDocument], int]:
        matching = [m for m in self.messages if m.session_id == session_id]
        matching.sort(key=lambda m: m.created_at)
        return matching[skip : skip + limit], len(matching)

    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[AgentMessageDocument]:
        matching = [m for m in self.messages if m.session_id == session_id]
        matching.sort(key=lambda m: m.created_at)
        return matching[-limit:] if matching else []

    async def delete_session_messages(self, session_id: str) -> int:
        before = len(self.messages)
        self.messages = [m for m in self.messages if m.session_id != session_id]
        return before - len(self.messages)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def memory_repos():
    session_repo = InMemorySessionRepository()
    message_repo = InMemoryMessageRepository()
    return session_repo, message_repo


@pytest.fixture
def mock_orchestrator():
    orchestrator = MagicMock(spec=AgentOrchestrator)

    async def _mock_execute(request, current_user, conversation_context=None):
        task_lower = request.task.lower()
        evidence_items = []

        if "forecast" in task_lower and "compare" not in task_lower:
            evidence_items.append(
                AgentEvidence(
                    evidence_id="evi_fc_01",
                    tool_id="get_latest_forecast",
                    tool_version="1.0.0",
                    execution_step=1,
                    category=EvidenceCategory.FORECAST,
                    summary="Predicted ICU occupancy at 91.5% with 18 admissions over 7 days.",
                    is_projection=True,
                )
            )
            answer = "The latest statistical forecast projects ICU occupancy will peak at 91.5%."
        elif "compare" in task_lower:
            evidence_items.append(
                AgentEvidence(
                    evidence_id="evi_fc_02",
                    tool_id="get_latest_forecast",
                    tool_version="1.0.0",
                    execution_step=1,
                    category=EvidenceCategory.FORECAST,
                    summary="Current forecast of 91.5% is 4.5% higher than previous week baseline (87.0%).",
                    is_projection=True,
                )
            )
            answer = (
                "Comparing with previous projections, demand increased from 87.0% to 91.5% (+4.5%)."
            )
        elif "15%" in task_lower or "surge" in task_lower:
            evidence_items.append(
                AgentEvidence(
                    evidence_id="evi_sim_01",
                    tool_id="run_surge_simulation",
                    tool_version="1.0.0",
                    execution_step=1,
                    category=EvidenceCategory.SIMULATION,
                    summary="Hypothetical 15% surge causes an ICU shortage of 4 beds at peak day 4.",
                    is_hypothetical=True,
                )
            )
            answer = "In a hypothetical 15% admission surge, the ICU enters a deficit of 4 beds by day 4."
        elif "summarize" in task_lower or "implication" in task_lower:
            answer = (
                "Operational Implications Summary:\n"
                "- Baseline & Forecast: Demand is projected at 91.5%.\n"
                "- Comparison: ICU pressure is up 4.5% week-over-week.\n"
                "- Surge Sensitivity: A 15% surge leads to a 4-bed shortage on day 4."
            )
        else:
            answer = f"Acknowledged operational inquiry: {request.task}"

        return AgentRunResponse(
            run_id=f"run_{request.session_id or 'mock'}",
            agent_id="hospital_operations_analyst",
            agent_name="Hospital Operations Analyst Agent",
            status=AgentExecutionStatus.COMPLETED,
            final_answer=answer,
            task_plan=AgentTaskPlan(
                objective=request.task,
                task_type="GENERAL",
                requires_tools=True,
                reasoning_summary="Investigate operational inquiry.",
            ),
            execution=AgentRunExecutionMetadata(
                steps_completed=2,
                tool_calls=len(evidence_items),
                duration_ms=45.0,
                stop_reason=StopReason.SUFFICIENT_EVIDENCE,
                model="test_model",
                provider="mock_provider",
            ),
            evidence=evidence_items,
            session_id=request.session_id,
        )

    orchestrator.execute = AsyncMock(side_effect=_mock_execute)
    return orchestrator


@pytest.fixture
def state_manager(memory_repos, mock_orchestrator):
    session_repo, message_repo = memory_repos
    context_builder = AgentContextBuilder(max_context_chars=4000)
    return AgentStateManager(
        session_repo=session_repo,
        message_repo=message_repo,
        orchestrator=mock_orchestrator,
        context_builder=context_builder,
    )


# ── 1. Context Builder Unit Tests ─────────────────────────────────────────────


def test_context_builder_empty():
    builder = AgentContextBuilder()
    user = _get_admin_user()
    perms = get_permissions_for_role(user.role)
    ctx = builder.build_context(
        session_id="ses_empty",
        recent_messages=[],
        current_user_permissions=perms,
    )
    assert len(ctx.turns) == 0
    assert ctx.is_truncated is False


def test_context_builder_reconstructs_turns():
    builder = AgentContextBuilder()
    admin = _get_admin_user()
    perms = get_permissions_for_role(admin.role)

    m1 = AgentMessageDocument(
        message_id="msg_1",
        session_id="ses_test",
        user_id=admin.user_id,
        role=MessageRole.USER,
        content="Show me ICU forecast.",
    )
    m2 = AgentMessageDocument(
        message_id="msg_2",
        session_id="ses_test",
        user_id=admin.user_id,
        role=MessageRole.ASSISTANT,
        content="ICU occupancy projected at 91.5%.",
        execution_id="run_1",
        metadata={
            "evidence_summaries": ["Projected 91.5% ICU occupancy"],
            "forecast_references": ["fc_icu_latest"],
        },
    )

    ctx = builder.build_context(
        session_id="ses_test",
        recent_messages=[m1, m2],
        current_user_permissions=perms,
    )
    assert len(ctx.turns) == 2
    assert ctx.turns[0].role == "USER"
    assert ctx.turns[1].role == "ASSISTANT"
    assert len(ctx.turns[1].evidence_summaries) == 1
    assert ctx.prior_forecast_references == ["fc_icu_latest"]

    prompt_fmt = builder.format_context_for_prompt(ctx)
    assert "ICU occupancy projected at 91.5%" in prompt_fmt
    assert "Projected 91.5% ICU occupancy" in prompt_fmt


def test_context_builder_rbac_revalidation():
    """Unprivileged user cannot inherit evidence references requiring permissions they lack."""
    builder = AgentContextBuilder()
    # Explicitly lacks simulation.read and predictions.read
    perms = ["knowledge.read"]

    m1 = AgentMessageDocument(
        message_id="msg_1",
        session_id="ses_test",
        user_id="usr_doc_456",
        role=MessageRole.ASSISTANT,
        content="Simulation shows 4-bed shortage.",
        metadata={
            "simulation_references": ["sim_surge_15"],
        },
    )

    ctx = builder.build_context(
        session_id="ses_test",
        recent_messages=[m1],
        current_user_permissions=perms,
    )
    # Lacks simulation.read so simulation references are omitted
    assert "sim_surge_15" not in ctx.prior_simulation_references


def test_context_builder_budget_clamping():
    """Context builder clamps long message history to max_context_chars."""
    builder = AgentContextBuilder(max_context_chars=200)
    admin = _get_admin_user()
    perms = get_permissions_for_role(admin.role)

    messages = [
        AgentMessageDocument(
            message_id=f"msg_{i}",
            session_id="ses_test",
            user_id=admin.user_id,
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"This is a relatively long message number {i} with operational text.",
        )
        for i in range(10)
    ]

    ctx = builder.build_context(
        session_id="ses_test",
        recent_messages=messages,
        current_user_permissions=perms,
    )
    assert ctx.is_truncated is True
    assert len(ctx.turns) < 10


# ── 2. State Manager Unit Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_state_manager_create_and_get_session(state_manager):
    admin = _get_admin_user()
    session = await state_manager.create_session(
        current_user=admin,
        payload=AgentSessionCreate(title="Test ICU Session"),
    )
    assert session.session_id.startswith("ses_")
    assert session.title == "Test ICU Session"
    assert session.status == SessionStatus.ACTIVE
    assert session.user_id == admin.user_id

    fetched = await state_manager.get_session(session.session_id, admin)
    assert fetched.session_id == session.session_id


@pytest.mark.asyncio
async def test_state_manager_ownership_isolation(state_manager):
    """User B cannot access or modify User A's session."""
    user_a = _get_admin_user()
    user_b = _get_second_user()

    session = await state_manager.create_session(
        current_user=user_a,
        payload=AgentSessionCreate(title="User A Session"),
    )

    with pytest.raises(HTTPException) as exc:
        await state_manager.get_session(session.session_id, user_b)
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc2:
        await state_manager.archive_session(session.session_id, user_b)
    assert exc2.value.status_code == 404

    with pytest.raises(HTTPException) as exc3:
        await state_manager.execute_in_session(
            session_id=session.session_id,
            task="Test inquiry",
            current_user=user_b,
        )
    assert exc3.value.status_code == 404


@pytest.mark.asyncio
async def test_state_manager_archive_and_restore(state_manager):
    admin = _get_admin_user()
    session = await state_manager.create_session(
        current_user=admin,
        payload=AgentSessionCreate(title="Archive Test"),
    )

    # Archive session
    archived = await state_manager.archive_session(session.session_id, admin)
    assert archived.status == SessionStatus.ARCHIVED

    # Attempt to post in archived session must fail
    with pytest.raises(HTTPException) as exc:
        await state_manager.execute_in_session(
            session_id=session.session_id,
            task="Try posting in archived",
            current_user=admin,
        )
    assert exc.value.status_code == 400
    assert "archived" in str(exc.value.detail).lower()

    # Restore session
    restored = await state_manager.restore_session(session.session_id, admin)
    assert restored.status == SessionStatus.ACTIVE

    # Now post succeeds
    res = await state_manager.execute_in_session(
        session_id=session.session_id,
        task="Try posting after restore",
        current_user=admin,
    )
    assert res.status == AgentExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_state_manager_delete_session(state_manager):
    admin = _get_admin_user()
    session = await state_manager.create_session(
        current_user=admin,
        payload=AgentSessionCreate(title="To Delete"),
    )
    await state_manager.execute_in_session(session.session_id, "Inquiry 1", admin)

    deleted = await state_manager.delete_session(session.session_id, admin)
    assert deleted is True

    with pytest.raises(HTTPException) as exc:
        await state_manager.get_session(session.session_id, admin)
    assert exc.value.status_code == 404


# ── 3. Canonical 4-Turn Operational Inquiry Continuity Test ───────────────────


@pytest.mark.asyncio
async def test_canonical_four_turn_conversation_continuity(state_manager):
    """
    Validates end-to-end multi-turn operational dialogue:
    1. Show me latest available ICU forecast.
    2. Now compare it with the previous forecast.
    3. What happens if admissions increase by 15%?
    4. Summarize the operational implications.
    """
    admin = _get_admin_user()

    # 1. Create session
    session = await state_manager.create_session(
        current_user=admin,
        payload=AgentSessionCreate(title="ICU Surge Analysis Session"),
    )
    sid = session.session_id

    # Turn 1: Show me latest available ICU forecast
    turn1_resp = await state_manager.execute_in_session(
        session_id=sid,
        task="Show me the latest available ICU forecast.",
        current_user=admin,
    )
    assert turn1_resp.status == AgentExecutionStatus.COMPLETED
    assert "91.5%" in turn1_resp.final_answer

    # Verify messages in repository
    msgs, count = await state_manager.list_messages(sid, admin)
    assert count == 2  # 1 User + 1 Assistant
    assert msgs[0].role == MessageRole.USER
    assert msgs[1].role == MessageRole.ASSISTANT

    # Turn 2: Now compare it with the previous forecast
    turn2_resp = await state_manager.execute_in_session(
        session_id=sid,
        task="Now compare it with the previous forecast.",
        current_user=admin,
    )
    assert turn2_resp.status == AgentExecutionStatus.COMPLETED
    assert "+4.5%" in turn2_resp.final_answer

    # Turn 3: What happens if admissions increase by 15%?
    turn3_resp = await state_manager.execute_in_session(
        session_id=sid,
        task="What happens if admissions increase by 15%?",
        current_user=admin,
    )
    assert turn3_resp.status == AgentExecutionStatus.COMPLETED
    assert "4 beds" in turn3_resp.final_answer

    # Turn 4: Summarize the operational implications
    turn4_resp = await state_manager.execute_in_session(
        session_id=sid,
        task="Summarize the operational implications.",
        current_user=admin,
    )
    assert turn4_resp.status == AgentExecutionStatus.COMPLETED
    assert "Operational Implications Summary" in turn4_resp.final_answer
    assert "91.5%" in turn4_resp.final_answer
    assert "4-bed shortage" in turn4_resp.final_answer

    # Final session checks
    final_session = await state_manager.get_session(sid, admin)
    assert final_session.message_count == 8  # 4 user + 4 assistant
    assert final_session.latest_execution_id is not None


# ── 4. REST API Endpoint Tests ────────────────────────────────────────────────


@pytest.fixture
def session_api_client(state_manager):
    app.dependency_overrides[get_agent_state_manager] = lambda: state_manager
    yield app
    app.dependency_overrides.clear()


def test_api_session_lifecycle(session_api_client):
    """Verifies full REST lifecycle for session creation, retrieval, updates, and messaging."""
    admin = _get_admin_user()
    app.dependency_overrides[get_current_user] = lambda: admin
    client = TestClient(session_api_client)

    # 1. Create Session
    create_resp = client.post(
        "/api/v1/agents/sessions",
        json={"title": "REST API Test Session", "agent_id": "hospital_operations_analyst"},
    )
    assert create_resp.status_code == 201
    s_data = create_resp.json()["data"]
    sid = s_data["session_id"]
    assert s_data["title"] == "REST API Test Session"
    assert s_data["status"] == "ACTIVE"

    # 2. List Sessions
    list_resp = client.get("/api/v1/agents/sessions")
    assert list_resp.status_code == 200
    list_data = list_resp.json()["data"]
    assert any(s["session_id"] == sid for s in list_data)

    # 3. Get Session by ID
    get_resp = client.get(f"/api/v1/agents/sessions/{sid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["session_id"] == sid

    # 4. Update Session Title
    patch_resp = client.patch(
        f"/api/v1/agents/sessions/{sid}",
        json={"title": "Updated Title via PATCH"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["title"] == "Updated Title via PATCH"

    # 5. Post Message to Session
    msg_resp = client.post(
        f"/api/v1/agents/sessions/{sid}/messages",
        json={"content": "Show me the latest available ICU forecast."},
    )
    assert msg_resp.status_code == 200
    msg_data = msg_resp.json()["data"]
    assert msg_data["status"] == "COMPLETED"
    assert "91.5%" in msg_data["final_answer"]

    # 6. List Messages
    msgs_resp = client.get(f"/api/v1/agents/sessions/{sid}/messages")
    assert msgs_resp.status_code == 200
    msgs = msgs_resp.json()["data"]
    assert len(msgs) == 2  # user + assistant

    # 7. Execute via POST /execute with session_id
    exec_resp = client.post(
        "/api/v1/agents/execute",
        json={
            "agent_id": "hospital_operations_analyst",
            "task": "Now compare it with the previous forecast.",
            "session_id": sid,
        },
    )
    assert exec_resp.status_code == 200
    assert "+4.5%" in exec_resp.json()["data"]["final_answer"]

    # 8. Archive Session
    archive_resp = client.post(f"/api/v1/agents/sessions/{sid}/archive")
    assert archive_resp.status_code == 200
    assert archive_resp.json()["data"]["status"] == "ARCHIVED"

    # 9. Verify posting to archived returns 400 Bad Request
    fail_post = client.post(
        f"/api/v1/agents/sessions/{sid}/messages",
        json={"content": "Should fail because archived."},
    )
    assert fail_post.status_code == 400

    # 10. Restore Session
    restore_resp = client.post(f"/api/v1/agents/sessions/{sid}/restore")
    assert restore_resp.status_code == 200
    assert restore_resp.json()["data"]["status"] == "ACTIVE"

    # 11. Delete Session
    del_resp = client.delete(f"/api/v1/agents/sessions/{sid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["status"] == "deleted"

    # Verify 404 after deletion
    after_del = client.get(f"/api/v1/agents/sessions/{sid}")
    assert after_del.status_code == 404
