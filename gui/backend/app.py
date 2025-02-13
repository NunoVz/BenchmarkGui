from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import os
import shlex
import sys
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

SUDO_PASSWORD = "b1vbx11"
BENCHMARK_DIR = "/home/admin/BenchmarkGui/Tese-2"
BENCHMARK_SCRIPT = "benchmark.py"

LOG_FILES = {
    "benchmark": "benchmark-log.txt",
    "mininet": "mininet-log.txt",
    "controller": "controller-log.txt"
}

@app.route('/')
def index():
    return render_template("index.html")

def save_log_to_file(log_type, message):
    if log_type in LOG_FILES:
        with open(LOG_FILES[log_type], "a") as file:
            file.write(message + "\n")

def read_logs_from_file(log_type):
    if log_type in LOG_FILES and os.path.exists(LOG_FILES[log_type]):
        with open(LOG_FILES[log_type], "r") as file:
            return file.readlines()
    return []


@app.route("/get-logs/<log_type>", methods=["GET"])
def get_logs(log_type):
    logs = read_logs_from_file(log_type)
    return jsonify({"logs": logs})

@app.route("/clear-logs/<log_type>", methods=["POST"])
def clear_logs(log_type):
    if log_type in LOG_FILES:
        open(LOG_FILES[log_type], "w").close()  # Clear the log file
        return jsonify({"message": f"{log_type} logs cleared!"})
    return jsonify({"error": "Invalid log type"}), 400

def log_message(log_type, message):
    print(message)
    socketio.emit(f"{log_type}_log", {"log": message})  # Send to frontend
    save_log_to_file(log_type, message)  # Save log to file
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

        allowed_commands = ["sudo mn -c", "sudo mn"]
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

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=443, debug=True)
