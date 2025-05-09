import sys
import requests
import socketio
import prompt_toolkit as pt

# Configuration
BASE_URL = 'http://localhost:8080'


def main():
    # 1) Begin a new task to get a task_id
    try:
        resp = requests.get(f"{BASE_URL}/begin")
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to /begin: {e}")
        return

    data = resp.json()
    task_id = data.get('task_id')
    if not task_id:
        print(f"Invalid begin response: {data}")
        return

    print(f"Started task with ID: {task_id}\n")

    # 2) Connect to Socket.IO and join the task room
    sio = socketio.Client()

    @sio.event
    def connect():
        print("[SocketIO] Connected to server")
        sio.emit('join', {'task_id': task_id})
        print(f"[SocketIO] Joined room: {task_id}\n")

        # 3) Kick off the task via HTTP POST
        payload = pt.prompt("As a question about Flatland by Edwin Abbot:\n")
        try:
            ask_resp = requests.post(
                f"{BASE_URL}/ask",
                json={'task_id': task_id, 'payload': payload}
            )
            ask_resp.raise_for_status()
            print(f"Called /ask: {ask_resp.json()}\n")
        except Exception as e:
            print(f"Failed to /ask: {e}")
            sio.disconnect()

    @sio.on('progress')
    def on_progress(data):
        # data is a dict with 'progress' and 'message'
        print(f"[Progress] {data.get('progress')}% - {data.get('message')}")

    @sio.on('done')
    def on_done(data):
        print(f"\n[Done] Result: {data.get('result')}")
        sio.disconnect()
        sys.exit(0)
        
    @sio.on('final_error')
    def on_final_error(data):
        print(f"\n[Fatal Error] {data.get('message')}")
        sio.disconnect()
        sys.exit(1)
        

    @sio.on('error')
    def on_error(data):
        print(f"\n[Error] {data.get('message')}")
        
    @sio.on('message')
    def on_message(data):
        print(f"\n[message] {data.get('message')}")
        

    @sio.event
    def disconnect():
        print("[SocketIO] Disconnected from server")

    # 4) Start the connection
    try:
        sio.connect(BASE_URL)
        sio.wait()
    except Exception as e:
        print(f"Connection error: {e}")


if __name__ == '__main__':
    main()
