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

def start_mininet():
    """Starts Mininet and continuously captures its logs."""
    global mininet_process
    try:
        log_message("Starting Mininet in background mode...")

        # Ensure any existing Mininet is cleaned up
        os.system(f"echo {SUDO_PASSWORD} | sudo -S mn -c")

        # Launch Mininet interactively
        command = f"echo {SUDO_PASSWORD} | sudo -S mn"
        mininet_process = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Stream logs from Mininet
        def stream_logs():
            for line in iter(mininet_process.stdout.readline, ""):
                log_message(f"[Mininet] {line.strip()}")
            for line in iter(mininet_process.stderr.readline, ""):
                log_message(f"[Mininet ERROR] {line.strip()}")

        # Run streaming in a background thread
        threading.Thread(target=stream_logs, daemon=True).start()

    except Exception as e:
        log_message(f"ERROR: Failed to start Mininet - {str(e)}")

@app.route("/start-mininet", methods=["POST"])
def start_mininet_endpoint():
    """API endpoint to start Mininet and stream logs."""
    socketio.start_background_task(target=start_mininet)
    return jsonify({"message": "Mininet started, logs streaming"}), 200

@app.route("/run-mininet-command", methods=["POST"])
def run_mininet_command():
    """Runs Mininet CLI commands and streams the output."""
    try:
        if mininet_process is None:
            return jsonify({"error": "Mininet is not running!"}), 400

        data = request.json
        command = data.get("command", "").strip()

        if not command:
            return jsonify({"error": "No command provided"}), 400

        log_message(f"Executing Mininet Command: {command}")

        # Send the command to Mininet's stdin
        mininet_process.stdin.write(command + "\n")
        mininet_process.stdin.flush()

        return jsonify({"message": f"Command '{command}' executed"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to execute Mininet command: {str(e)}"}), 500

@app.route("/stop-mininet", methods=["POST"])
def stop_mininet():
    """Stops Mininet and cleans up."""
    global mininet_process
    if mininet_process:
        mininet_process.stdin.write("exit\n")
        mininet_process.stdin.flush()
        mininet_process.terminate()
        mininet_process = None
        log_message("Mininet stopped.")
        return jsonify({"message": "Mininet stopped successfully"}), 200
    return jsonify({"error": "Mininet is not running!"}), 400

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=443, debug=True)
