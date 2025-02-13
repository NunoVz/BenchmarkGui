from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import os
import shlex
import sys
import json

app = Flask(__name__, static_folder="static", template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*")

SUDO_PASSWORD = "b1vbx11"
BENCHMARK_DIR = "/home/admin/BenchmarkGui/Tese-2"
BENCHMARK_SCRIPT = "benchmark.py"

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
            log_message(f"⚠ ERROR: Directory '{BENCHMARK_DIR}' not found!")
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
            log_message(f"⚠ ERROR: {line.strip()}")

        process.stdout.close()
        process.stderr.close()
        process.wait()

        if process.returncode != 0:
            log_message(f"⚠ ERROR: Benchmark tool exited with code {process.returncode}")

        log_message("✅ Benchmark process completed.")
        socketio.emit("benchmark_complete", {"message": "Benchmark process completed."})

    except Exception as e:
        log_message(f"❌ Failed to execute benchmark tool: {e}")

@app.route('/reset-mininet', methods=['POST'])
def reset_mininet():
    try:
        command = f"echo {SUDO_PASSWORD} | sudo -S mn -c"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            return jsonify({"message": "✅ Mininet reset successfully!"}), 200
        else:
            return jsonify({"message": f"❌ Error resetting Mininet: {result.stderr}"}), 500

    except Exception as e:
        return jsonify({"message": f"❌ Failed to execute reset: {e}"}), 500

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

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=443, debug=True)
