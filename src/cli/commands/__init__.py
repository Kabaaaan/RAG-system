from __future__ import annotations

from src.cli.commands.db import init_db_command
from src.cli.commands.recommendations import (
    add_recommendation_command,
    generate_recommendation_command,
    show_recommendations_command,
)

ALL_COMMANDS = (
    init_db_command,
    add_recommendation_command,
    generate_recommendation_command,
    show_recommendations_command,
)
