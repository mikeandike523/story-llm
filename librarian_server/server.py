import eventlet
eventlet.monkey_patch()

import uuid
from dataclasses import asdict
from answer_question import answer_question
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, join_room
from server_types import TaskBeginResponse, TaskRequest


app = Flask(__name__)

CORS(app)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*', logger=True, engineio_logger=True)

@socketio.on('connect', namespace='/librarian-server')
def handle_connect():
    print("Client connected to /librarian-server")
    # any initialization …

@socketio.on('disconnect', namespace='/librarian-server')
def handle_disconnect():
    print("Client disconnected from /librarian-server")

@app.route('/begin', methods=['GET'])
def begin_task():
    task_id = uuid.uuid4()
    response = TaskBeginResponse(task_id=task_id)
    return jsonify(asdict(response))

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    task_request = TaskRequest(
        task_id=uuid.UUID(data['task_id']),
        payload=data['payload']
    )

    # Start task in background
    socketio.start_background_task(answer_question, socketio, task_request)
    return {"status": "task started"}

@socketio.on('join')
def on_join(data):
    task_id = data.get('task_id')
    join_room(str(task_id))  # join room with task_id as name
    print(f"Client joined room {task_id}")

if __name__ == '__main__':
    socketio.run(
        app,
        host="0.0.0.0",
        port=8080,
        debug=True,
        # you can explicitly choose eventlet if you have multiple servers installed
        # async_mode='eventlet',
    )
