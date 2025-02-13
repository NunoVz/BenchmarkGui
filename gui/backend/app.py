from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import paramiko
import threading
import subprocess
import shlex
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# SUDO PASSWORD (Consider using sudoers instead)
SUDO_PASSWORD = "b1vbx11"

# Path to Benchmark Tool
BENCHMARK_DIR = "/home/admin/BenchmarkTool"

# Controller VM (SSH)
CONTROLLER_VM = {
    "ip": "10.3.3.100",
    "username": "admin",
    "command": "sudo tail -f /var/log/controller.log"
}
SSH_KEY_PATH = "/home/admin/.ssh/id_rsa"

# Commands to Execute
COMMANDS = {
    "mininet": f"echo {SUDO_PASSWORD} | sudo -S mn --test pingall",
    "benchmark_tool": f"echo {SUDO_PASSWORD} | sudo -S python3 {BENCHMARK_DIR}/benchmark.py -ip 10.3.3.114 -p 6653 -s 12 -q 3 -max 30 -n onos -t 3-tier -m N"
}

def stream_local_cli(command_name, command):
    """ Runs a CLI command, streams output, and captures errors. """
    try:
        print(f"Executing: {command}")  # Debug: Show command being executed
        
        # Run the command with unbuffered output (forces real-time streaming)
        process = subprocess.Popen(
            shlex.split(command),  # Split command into list for security
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffering for real-time output
        )

        # Read stdout and stderr line by line
        for line in iter(process.stdout.readline, ""):
            print(f"{command_name} OUTPUT: {line.strip()}")  # Debug: Show logs
            socketio.emit(f"log_update_{command_name}", {"log": line.strip()})

        for line in iter(process.stderr.readline, ""):
            print(f"{command_name} ERROR: {line.strip()}")  # Debug: Show errors
            socketio.emit(f"log_update_{command_name}", {"log": f"ERROR: {line.strip()}"})

        process.stdout.close()
        process.stderr.close()
        process.wait()

        if process.returncode != 0:
            error_msg = f"⚠ ERROR: {command_name} exited with code {process.returncode}"
            print(error_msg)
            socketio.emit(f"log_update_{command_name}", {"log": error_msg})

    except Exception as e:
        error_msg = f"❌ Failed to execute {command_name}: {e}"
        print(error_msg)
        socketio.emit(f"log_update_{command_name}", {"log": error_msg})


def start_log_threads():
    """ Starts threads for Mininet & Benchmark tool logs. """
    for command_name, command in COMMANDS.items():
        threading.Thread(target=stream_local_cli, args=(command_name, command), daemon=True).start()


@app.route('/start-benchmark', methods=['POST'])
def start_benchmark():
    """ Starts the benchmark tool and logs streaming. """
    data = request.json
    print(f"Received request: {data}")  # Debug: Show received request
    start_log_threads()
    return jsonify({"message": "Benchmark started, CLI logs streaming", "received_data": data}), 200


if __name__ == '__main__':
    print("Flask server starting on 127.0.0.1:5000...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
