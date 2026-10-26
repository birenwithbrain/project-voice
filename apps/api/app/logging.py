import logging


def configure_logging(level: str) -> None:
    """Configure concise operational logging without recording user content."""

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
