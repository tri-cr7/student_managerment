"""Controllers."""
from studentapp.controllers import auth_controller, user_controller, profile_controller, health_controller

ALL_BLUEPRINTS = [health_controller.bp, auth_controller.bp, profile_controller.bp, user_controller.bp]
