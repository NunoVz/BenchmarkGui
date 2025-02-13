from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import paramiko
import threading
import subprocess

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# SUDO PASSWORD (This is insecure; consider using sudoers file instead)
SUDO_PASSWORD = "b1vbx11"

# Controller VM (External - Needs SSH)
CONTROLLER_VM = {
    "ip": "10.3.3.100",
    "username": "admin",
    "command": "sudo tail -f /var/log/controller.log"  # Change to actual controller command
}
SSH_KEY_PATH = "/home/admin/.ssh/id_rsa"

# Local CLI commands (require sudo)
COMMANDS = {
    "mininet": f"echo {SUDO_PASSWORD} | sudo -S mn --test pingall",  # Example, replace with actual Mininet CLI command
    "benchmark_tool": f"echo {SUDO_PASSWORD} | sudo -S python3 benchmark.py -ip 10.3.3.114 -p 6653 -s 12 -q 3 -max 30 -n onos -t 3-tier -m N"
}

def stream_local_cli(command_name, command):
    """ Runs a CLI command and streams output, handling sudo password. """
    try:
        print(f"Running command: {command}")  # Log the command being executed
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in iter(process.stdout.readline, ""):
            socketio.emit(f"log_update_{command_name}", {"log": line.strip()})

        process.stdout.close()
        process.wait()
    except Exception as e:
        socketio.emit(f"log_update_{command_name}", {"log": f"Error running command: {e}"})


def stream_controller_cli():
    """ Connects to the Controller VM via SSH and streams CLI output. """
    try:
        print("Connecting to Controller VM via SSH...")  # Log SSH connection attempt
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(CONTROLLER_VM["ip"], username=CONTROLLER_VM["username"], key_filename=SSH_KEY_PATH)

        print(f"Running Controller command: {CONTROLLER_VM['command']}")  # Log command
        _, stdout, _ = client.exec_command(CONTROLLER_VM["command"])

        for line in iter(stdout.readline, ""):
            socketio.emit("log_update_controller", {"log": line.strip()})

        client.close()
    except Exception as e:
        socketio.emit("log_update_controller", {"log": f"Error fetching logs: {e}"})


def start_log_threads():
    """ Starts CLI streaming threads. """
    threading.Thread(target=stream_controller_cli, daemon=True).start()
    for command_name, command in COMMANDS.items():
        threading.Thread(target=stream_local_cli, args=(command_name, command), daemon=True).start()


@app.route('/start-benchmark', methods=['POST'])
def start_benchmark():
    """ Starts CLI commands and streams output, logs received parameters. """
    data = request.json
    print(f"Received request: {data}")  # Log what React is sending
    start_log_threads()
    return jsonify({"message": "Benchmark started, CLI logs streaming", "received_data": data}), 200


if __name__ == '__main__':
    print("Flask server starting on 127.0.0.1:5000...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
