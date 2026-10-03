"""FastAPI dependencies that expose the application container to route handlers."""

from typing import Annotated

from fastapi import Depends, Request

from app.ai.agent import HomeAgent
from app.ai.history import InMemoryAgentHistory
from app.container import Container
from app.domain.command_service import CommandService
from app.domain.home_state import HomeState
from app.events.store import EventStore
from app.gestures.history import GestureHistory
from app.gestures.service import GestureService


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_home_state(container: ContainerDep) -> HomeState:
    return container.home_state


def get_command_service(container: ContainerDep) -> CommandService:
    return container.command_service


def get_event_store(container: ContainerDep) -> EventStore:
    return container.event_store


def get_gesture_service(container: ContainerDep) -> GestureService:
    return container.gesture_service


def get_gesture_history(container: ContainerDep) -> GestureHistory:
    return container.gesture_history


HomeStateDep = Annotated[HomeState, Depends(get_home_state)]
CommandServiceDep = Annotated[CommandService, Depends(get_command_service)]
EventStoreDep = Annotated[EventStore, Depends(get_event_store)]
GestureServiceDep = Annotated[GestureService, Depends(get_gesture_service)]
GestureHistoryDep = Annotated[GestureHistory, Depends(get_gesture_history)]


def get_agent(container: ContainerDep) -> HomeAgent:
    return container.agent


def get_agent_history(container: ContainerDep) -> InMemoryAgentHistory:
    return container.agent_history


AgentDep = Annotated[HomeAgent, Depends(get_agent)]
AgentHistoryDep = Annotated[InMemoryAgentHistory, Depends(get_agent_history)]
