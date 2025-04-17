from flask_socketio import SocketIO
from server_types import ProgressUpdate, TaskDone, TaskError, TaskMessage
from uuid import UUID

def emit_message(socketio: SocketIO, task_id: UUID, message: str):
    payload = TaskMessage(message=message)
    socketio.emit("message", payload.__dict__, room=str(task_id))

def emit_progress(socketio: SocketIO, task_id: UUID, progress: int, message: str):
    payload = ProgressUpdate(progress=progress, message=message)
    socketio.emit("progress", payload.__dict__, room=str(task_id))

def emit_done(socketio: SocketIO, task_id: UUID, result: str):
    payload = TaskDone(result=result)
    socketio.emit("done", payload.__dict__, room=str(task_id))
    
def emit_error(socketio: SocketIO, task_id: UUID, error_message: str):
    payload = TaskError(message=error_message)
    socketio.emit("error", payload.__dict__, room=str(task_id))
    
def emit_final_error(socketio: SocketIO, task_id: UUID, error_message: str):
    payload = TaskError(message=error_message)
    socketio.emit("final_error", payload.__dict__, room=str(task_id))


