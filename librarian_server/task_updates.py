from flask_socketio import SocketIO
from server_types import ProgressUpdate, TaskDone, TaskError, TaskMessage
from uuid import UUID

def emit_message(socketio: SocketIO, task_id: UUID, message: str):
    payload = TaskMessage(message=message)
    print(f"[SocketIO] Sending message to room {task_id}: {message}")
    socketio.emit("message", payload.__dict__, room=str(task_id))

def emit_progress(socketio: SocketIO, task_id: UUID, progress: int, message: str):
    payload = ProgressUpdate(progress=progress, message=message)
    print(f"[SocketIO] Sending progress to room {task_id}: {progress}% - {message}")
    socketio.emit("progress", payload.__dict__, room=str(task_id))

def emit_done(socketio: SocketIO, task_id: UUID, result: str):
    payload = TaskDone(result=result)
    print(f"[SocketIO] Sending done to room {task_id}: {result}")
    socketio.emit("done", payload.__dict__, room=str(task_id))
    
def emit_error(socketio: SocketIO, task_id: UUID, error_message: str):
    payload = TaskError(message=error_message)
    print(f"[SocketIO] Sending error to room {task_id}: {error_message}")
    socketio.emit("error", payload.__dict__, room=str(task_id))
    
def emit_final_error(socketio: SocketIO, task_id: UUID, error_message: str):
    payload = TaskError(message=error_message)
    print(f"[SocketIO] Sending final error to room {task_id}: {error_message}")
    socketio.emit("final_error", payload.__dict__, room=str(task_id))


