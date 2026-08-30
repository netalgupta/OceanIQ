"""
VARUNA — Main Application Entrypoint
Fusing INCOIS ARGO Physical Oceanography with CMLRE Marine Living Resources.
"""

from __future__ import annotations

import logging
import sys

try:
    import structlog  # type: ignore
    _has_structlog = True
except ImportError:
    structlog = None  # type: ignore
    _has_structlog = False

# Export FastAPI app for `uvicorn main:app`
from src.api.app import app


def setup_logging():
    """Configure standard logging with optional structlog enhancement."""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    if _has_structlog and structlog is not None:
        try:
            structlog.configure(
                processors=[
                    structlog.stdlib.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.dev.ConsoleRenderer(colors=True),
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            # Hijack uvicorn loggers
            for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
                logger = logging.getLogger(logger_name)
                logger.handlers.clear()
                logger.propagate = True
        except Exception:
            pass


if __name__ == "__main__":
    setup_logging()

    import uvicorn
    from src.config import settings

    reload = settings.app_env.lower() in ("dev", "development")

    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
        log_level="info",
        server_header=False,
    )
