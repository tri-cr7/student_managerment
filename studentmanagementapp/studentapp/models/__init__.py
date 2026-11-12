"""Entities."""
from studentapp.models.user import User, UserRoleEnum
from studentapp.models.system_rule import SystemRule, DEFAULT_RULES
from studentapp.models.audit_log import AuditLog
from studentapp.models.password_otp import PasswordOtp, OtpPurpose
from studentapp.models.academic_year import AcademicYear
from studentapp.models.semester import Semester
from studentapp.models.grade import Grade
from studentapp.models.student import Student, StudentStatusEnum
from studentapp.models.class_room import Class
from studentapp.models.subject import Subject
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.teaching_assignment import TeachingAssignment
from studentapp.models.score import Score, ALL_SCORE_COLUMNS, SCORE_GROUPS
from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum
from studentapp.models.score_change_request import ScoreChangeRequest, ChangeRequestStatusEnum
from studentapp.models.score_change_detail import ScoreChangeDetail, ChangeDetailStatusEnum
from studentapp.models.email_outbox import EmailOutbox

__all__ = [
    "User",
    "UserRoleEnum",
    "SystemRule",
    "DEFAULT_RULES",
    "AuditLog",
    "PasswordOtp",
    "OtpPurpose",
    "AcademicYear",
    "Semester",
    "Grade",
    "Student",
    "StudentStatusEnum",
    "Class",
    "Subject",
    "ClassEnrollment",
    "EnrollmentStatusEnum",
    "TeachingAssignment",
    "Score",
    "ALL_SCORE_COLUMNS",
    "SCORE_GROUPS",
    "ScoreSubmission",
    "SubmissionStatusEnum",
    "ScoreChangeRequest",
    "ChangeRequestStatusEnum",
    "ScoreChangeDetail",
    "ChangeDetailStatusEnum",
    "EmailOutbox",
]
