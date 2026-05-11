# app/models/__init__.py
# Importing models here lets other files write:
#   from app.models import User, Task
# instead of:
#   from app.models.user import User
#   from app.models.task import Task

from app.models.user import User
from app.models.task import Task, Priority, Status