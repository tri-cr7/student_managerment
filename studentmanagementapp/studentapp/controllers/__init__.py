"""Controllers."""
from studentapp.controllers import (
    auth_controller,
    health_controller,
    profile_controller,
    teacher_controller,
    user_controller,
)

ALL_BLUEPRINTS = [
    health_controller.bp,
    auth_controller.bp,
    profile_controller.bp,
    user_controller.bp,
    teacher_controller.bp,
]
