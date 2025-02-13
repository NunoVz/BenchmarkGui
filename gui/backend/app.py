from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import os
import shlex
import sys
import json
import paramiko


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

SUDO_PASSWORD = "b1vbx11"
BENCHMARK_DIR = "/home/admin/BenchmarkGui/Tese-2"
BENCHMARK_SCRIPT = "benchmark.py"
CONTROLLER_IP = "193.137.203.34"
CONTROLLER_USER = "admin"
CONTROLLER_KEY = "/home/admin/.ssh/id_rsa"

LOG_FILES = {
    "onos": "/opt/onos/logs/karaf.log",
    "ryu": "/var/log/ryu.log",
    "odl": "/opt/opendaylight/data/log/karaf.log",
    "floodlight": "/var/log/floodlight.log"
}

@app.route('/')
def index():
    return render_template("index.html")

def log_message(message):
    print(message)
    socketio.emit("log_update", {"log": message})
    sys.stdout.flush()

def stream_benchmark_logs(command):
    try:
        if not os.path.exists(BENCHMARK_DIR):
            log_message(f"ERROR: Directory '{BENCHMARK_DIR}' not found!")
            return

        log_message(f"Executing: {command}")

        process = subprocess.Popen(
            shlex.split(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=BENCHMARK_DIR  
        )

        process.stdin.write(SUDO_PASSWORD + "\n")
        process.stdin.flush()

        for line in iter(process.stdout.readline, ""):
            log_message(f"{line.strip()}")

        for line in iter(process.stderr.readline, ""):
            log_message(f"ERROR: {line.strip()}")

        process.stdout.close()
        process.stderr.close()
        process.wait()

        if process.returncode != 0:
            log_message(f"ERROR: Benchmark tool exited with code {process.returncode}")

        log_message("Benchmark process completed.")
        socketio.emit("benchmark_complete", {"message": "Benchmark process completed."})

    except Exception as e:
        log_message(f"Failed to execute benchmark tool: {e}")

@app.route('/start-benchmark', methods=['POST'])
def start_benchmark():
    data = request.json

    command = f"sudo -S python3 {BENCHMARK_DIR}/{BENCHMARK_SCRIPT} "
    command += f"-ip {data.get('controller_ip', 'localhost')} "
    command += f"-p {data.get('controller_port', '6653')} "
    command += f"-n {data.get('controller_name', 'onos')} "
    command += f"-t {data.get('topology', '3-tier')} "
    command += f"-m {data.get('metrics', 'TDT')} "
    command += f"-s {data.get('start', '12')} "
    command += f"-q {data.get('query_interval', '3')} "
    command += f"-max {data.get('maxsize', '30')} "

    log_message(f"Received benchmark start request. Running: {command}")

    socketio.start_background_task(target=stream_benchmark_logs, command=command)

    return jsonify({"message": "Benchmark started, logs streaming"}), 200

@app.route('/run-mininet-command', methods=['POST'])
def run_mininet_command():
    try:
        data = request.json
        command = data.get("command", "").strip()

        allowed_commands = ["sudo mn -c", "sudo mn", "sudo mn --log-level=debug", "sudo tcpdump -i any -n -X port 6633"]
        if command not in allowed_commands:
            return jsonify({"error": "Unauthorized command!"}), 400

        full_command = f"echo {SUDO_PASSWORD} | sudo -S {command}"

        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        if stdout:
            socketio.emit("mininet_log", {"log": stdout.strip()})
        if stderr:
            socketio.emit("mininet_log", {"log": f'ERROR: {stderr.strip()}'})

        return jsonify({"output": stdout.strip() if stdout else stderr.strip()}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to execute command: {str(e)}"}), 500


def stream_controller_logs(controller_name):
    if controller_name not in LOG_FILES:
        socketio.emit("controller_log", {"log": f"ERROR: Unknown controller {controller_name}"})
        return
    
    log_file = LOG_FILES[controller_name]

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(CONTROLLER_IP, username=CONTROLLER_USER, key_filename=CONTROLLER_KEY)
        print(f"Connected to {controller_name} controller at {CONTROLLER_IP}")

        command = f"tail -f {log_file}"
        stdin, stdout, stderr = client.exec_command(command)

        for line in iter(stdout.readline, ""):
            socketio.emit("controller_log", {"log": line.strip()})
        
        client.close()

    except Exception as e:
        socketio.emit("controller_log", {"log": f"ERROR: Failed to fetch logs: {str(e)}"})

@app.route('/start-controller-logs', methods=['POST'])
def start_controller_logs():
    data = request.json
    controller_name = data.get("controller_name", "onos")  
    
    socketio.start_background_task(stream_controller_logs, controller_name)

    return jsonify({"message": f"Streaming logs from {controller_name}"}), 200


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=443, debug=True)
