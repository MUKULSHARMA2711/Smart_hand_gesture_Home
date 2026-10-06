"""FastAPI application factory. Run with ``uvicorn app.main:app --reload``."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.providers import AIProvider
from app.api.errors import register_exception_handlers
from app.api.schemas import RootResponse
from app.api.v1.router import api_router
from app.config import Settings, get_settings
from app.container import build_container
from app.mqtt.client import MQTTTransport


def create_app(
    settings: Settings | None = None,
    *,
    ai_provider: AIProvider | None = None,
    mqtt_transport: MQTTTransport | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    container = build_container(settings, ai_provider=ai_provider, mqtt_transport=mqtt_transport)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # MQTT connects in the background: startup never waits for (or fails on) the broker.
        if container.mqtt is not None:
            await container.mqtt.start()
        try:
            yield
        finally:
            if container.mqtt is not None:
                await container.mqtt.stop()

    app = FastAPI(
        lifespan=lifespan,
        title=settings.app_name,
        version="0.1.0",
        description="Virtual IoT backend for IntelliHome. Devices are simulated in memory "
        "behind the same abstraction that ESP32/MQTT hardware will implement.",
    )
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", response_model=RootResponse, tags=["meta"], summary="Service info")
    async def root() -> RootResponse:
        return RootResponse(
            name=settings.app_name,
            description="AI-powered smart home automation system",
            status="operational",
            docs=app.docs_url,
            api=settings.api_prefix,
        )

    return app


app = create_app()
