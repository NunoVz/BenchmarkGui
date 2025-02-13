from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import os
import shlex
import sys

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

SUDO_PASSWORD = "b1vbx11"
BENCHMARK_DIR = "/home/admin/BenchmarkGui/Tese-2"
BENCHMARK_CMD = f"sudo -S python3 {BENCHMARK_DIR}/benchmark.py -ip 193.137.203.34 -p 6653 -s 12 -q 3 -max 30 -n onos -t 3-tier -m N"

@app.route('/')
def index():
    return render_template("index.html")  # Serve the HTML page

def log_message(message):
    """ Sends logs to both Flask console and the Web via WebSockets. """
    print(message)
    socketio.emit("log_update", {"log": message})
    sys.stdout.flush()  # Ensure real-time log flushing

def stream_benchmark_logs():
    """ Runs benchmark.py and streams logs to the webpage. """
    try:
        if not os.path.exists(BENCHMARK_DIR):
            log_message(f"⚠ ERROR: Directory '{BENCHMARK_DIR}' not found!")
            return
        
        log_message(f"Executing: {BENCHMARK_CMD}")

        process = subprocess.Popen(
            shlex.split(BENCHMARK_CMD),
            stdin=subprocess.PIPE,  # Send sudo password
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Send sudo password
        process.stdin.write(SUDO_PASSWORD + "\n")
        process.stdin.flush()

        # Read stdout and stderr in real-time
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

@app.route('/start-benchmark', methods=['POST'])
def start_benchmark():
    """ Starts the benchmark and logs streaming. """
    log_message("Received benchmark start request.")
    socketio.start_background_task(target=stream_benchmark_logs)
    return jsonify({"message": "Benchmark started, logs streaming"}), 200

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=443, debug=True)
