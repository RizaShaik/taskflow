# app/services/__init__.py
# Clean imports — other files can write:
#   from app.services import AuthService, TaskService

from app.services.auth_service import AuthService
from app.services.task_service import TaskService