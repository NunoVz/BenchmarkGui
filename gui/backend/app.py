from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import paramiko
import threading
import subprocess
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# SUDO PASSWORD (Consider using sudoers instead)
SUDO_PASSWORD = "b1vbx11"

# Controller VM (External - Needs SSH)
CONTROLLER_VM = {
    "ip": "10.3.3.100",
    "username": "admin",
    "command": "sudo tail -f /var/log/controller.log"  # Change this to the actual controller command
}
SSH_KEY_PATH = "/home/admin/.ssh/id_rsa"

# Path to the Benchmark Tool Folder (Modify this!)
BENCHMARK_DIR = "/home/admin/BenchmarkTool"

# Local CLI commands (use full paths to prevent errors)
COMMANDS = {
    "mininet": f"echo {SUDO_PASSWORD} | sudo -S mn --test pingall",  
    "benchmark_tool": f"echo {SUDO_PASSWORD} | sudo -S python3 {BENCHMARK_DIR}/benchmark.py -ip 10.3.3.114 -p 6653 -s 12 -q 3 -max 30 -n onos -t 3-tier -m N"
}

def stream_local_cli(command_name, command):
    """ Runs a CLI command, captures stdout and stderr, and sends logs to React. """
    try:
        print(f"Running command: {command}")  # Log the command

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Read stdout and stderr in real-time
        for line in process.stdout:
            socketio.emit(f"log_update_{command_name}", {"log": line.strip()})
        for line in process.stderr:
            socketio.emit(f"log_update_{command_name}", {"log": f"ERROR: {line.strip()}"})

        process.stdout.close()
        process.stderr.close()
        process.wait()

        if process.returncode != 0:
            socketio.emit(f"log_update_{command_name}", {"log": f"⚠ ERROR: {command_name} exited with code {process.returncode}"})

    except Exception as e:
        socketio.emit(f"log_update_{command_name}", {"log": f"❌ Failed to execute {command_name}: {e}"})


def start_log_threads():
    """ Starts CLI streaming threads. """
    for command_name, command in COMMANDS.items():
        threading.Thread(target=stream_local_cli, args=(command_name, command), daemon=True).start()


@app.route('/start-benchmark', methods=['POST'])
def start_benchmark():
    """ Starts CLI commands and streams output, logs received parameters. """
    data = request.json
    print(f"Received request: {data}")  # Log received request
    start_log_threads()
    return jsonify({"message": "Benchmark started, CLI logs streaming", "received_data": data}), 200


if __name__ == '__main__':
    print("Flask server starting on 127.0.0.1:5000...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
