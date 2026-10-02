"""FastAPI dependencies that expose the application container to route handlers."""

from typing import Annotated

from fastapi import Depends, Request

from app.container import Container
from app.domain.command_service import CommandService
from app.domain.home_state import HomeState
from app.events.store import EventStore


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_home_state(container: ContainerDep) -> HomeState:
    return container.home_state


def get_command_service(container: ContainerDep) -> CommandService:
    return container.command_service


def get_event_store(container: ContainerDep) -> EventStore:
    return container.event_store


HomeStateDep = Annotated[HomeState, Depends(get_home_state)]
CommandServiceDep = Annotated[CommandService, Depends(get_command_service)]
EventStoreDep = Annotated[EventStore, Depends(get_event_store)]
