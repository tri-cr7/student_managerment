"""Controllers."""
from studentapp.controllers import (
    academic_controller,
    academic_test_controller,
    auth_controller,
    catalog_controller,
    health_controller,
    profile_controller,
    report_controller,
    audit_controller,
    teacher_controller,
    user_controller,
    staff_controller,
    main_controller
)

ALL_BLUEPRINTS = [
    health_controller.bp,
    auth_controller.bp,
    profile_controller.bp,
    user_controller.bp,
    teacher_controller.bp,
    academic_controller.bp,
    catalog_controller.bp,
    report_controller.bp,
    audit_controller.bp,
    academic_test_controller.bp,
    staff_controller.bp,
    main_controller.bp
]
