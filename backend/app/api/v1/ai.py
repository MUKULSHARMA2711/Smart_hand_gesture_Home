from typing import Annotated

from fastapi import APIRouter, Query

from app.ai.models import AI_INTENTS, AgentResponse
from app.ai.providers import MockAIProvider
from app.api.deps import AgentDep, AgentHistoryDep, ContainerDep, HomeStateDep
from app.api.schemas import AICommandRequest, AIStatusResponse, DeviceCapabilities
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
        },
    )


@router.get("/history", response_model=list[AgentResponse], summary="Recent assistant interactions, newest first")
async def ai_history(history: AgentHistoryDep, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[AgentResponse]:
    return history.recent(limit=limit)
