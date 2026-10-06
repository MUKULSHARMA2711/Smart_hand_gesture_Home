from typing import Annotated

from fastapi import APIRouter, Query

from app.ai.models import AI_INTENTS, AgentResponse
from app.ai.providers import MockAIProvider
from app.api.deps import AgentDep, AgentHistoryDep, ContainerDep, HomeStateDep
from app.api.schemas import AICommandRequest, AIStatusResponse, ConfirmationDecision, DeviceCapabilities, ErrorResponse
from app.domain.policy import SECURITY_SENSITIVE_CAPABILITIES

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/command",
    response_model=AgentResponse,
    summary="Ask the AI agent to answer a question or control devices",
    description="The agent proposes a structured plan; every action is validated against device "
    "capabilities and the security policy before it runs through the CommandService "
    "(source=ai_agent). Rejected actions are reported, never executed.",
)
async def ai_command(request: AICommandRequest, agent: AgentDep) -> AgentResponse:
    return await agent.handle(request.message)


@router.post(
    "/confirmations/{confirmation_id}",
    response_model=AgentResponse,
    summary="Confirm or cancel a held security-sensitive action (door unlock)",
    description="Equivalent to answering 'yes, unlock it' or 'cancel'. A confirmed action is re-validated "
    "and executed through the CommandService (source=ai_agent).",
    responses={
        404: {"model": ErrorResponse, "description": "No pending confirmation with this id"},
        410: {"model": ErrorResponse, "description": "The confirmation expired; nothing was executed"},
    },
)
async def decide_confirmation(confirmation_id: str, request: ConfirmationDecision, agent: AgentDep) -> AgentResponse:
    return await agent.decide(confirmation_id, confirm=request.decision == "confirm")


@router.get("/status", response_model=AIStatusResponse, summary="AI provider and capability model")
async def ai_status(agent: AgentDep, home: HomeStateDep, container: ContainerDep) -> AIStatusResponse:
    return AIStatusResponse(
        provider=agent.provider.name,
        model=agent.provider.model,
        mock=isinstance(agent.provider, MockAIProvider),
        intents=sorted(AI_INTENTS),
        devices=[
            DeviceCapabilities(
                device_id=device.id,
                name=device.name,
                device_type=device.device_type,
                capabilities=device.spec.capabilities,
            )
            for device in home.devices.all()
        ],
        security_policy={
            "security_sensitive_capabilities": sorted(SECURITY_SENSITIVE_CAPABILITIES),
            "requires_explicit_request": True,
            "allow_unlock": container.settings.ai_allow_unlock,
            "unlock_requires_confirmation": container.settings.ai_unlock_requires_confirmation,
            "confirmation_timeout_s": container.settings.ai_confirmation_timeout_s,
        },
    )


@router.get("/history", response_model=list[AgentResponse], summary="Recent assistant interactions, newest first")
async def ai_history(history: AgentHistoryDep, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[AgentResponse]:
    return history.recent(limit=limit)
