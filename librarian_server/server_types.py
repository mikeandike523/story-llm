from dataclasses import dataclass
from uuid import UUID

@dataclass
class TaskBeginResponse:
    task_id: UUID

@dataclass
class TaskRequest:
    task_id: UUID
    payload: str  # Replace with actual business input structure if needed

@dataclass
class ProgressUpdate:
    progress: int
    message: str
    
@dataclass
class TaskMessage:
    message: str

@dataclass
class TaskDone:
    result: str
    
    
@dataclass
class TaskError:
    message: str

