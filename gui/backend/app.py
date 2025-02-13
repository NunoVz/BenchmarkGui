from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import subprocess
import os
import shlex

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# SUDO PASSWORD (Consider using sudoers instead)
SUDO_PASSWORD = "b1vbx11"

# Path to Benchmark Tool
BENCHMARK_DIR = "/home/admin/BenchmarkGui/Tese-2"
BENCHMARK_CMD = f"sudo -S python3 {BENCHMARK_DIR}/benchmark.py -ip 193.137.203.34 -p 6653 -s 12 -q 3 -max 30 -n onos -t 3-tier -m N"

def stream_benchmark_logs():
    """ Runs benchmark.py from the correct directory and streams logs. """
    try:
        if not os.path.exists(BENCHMARK_DIR):
            raise FileNotFoundError(f"⚠ ERROR: Directory '{BENCHMARK_DIR}' not found!")

        print(f"Executing: {BENCHMARK_CMD}")

        process = subprocess.Popen(
            shlex.split(BENCHMARK_CMD),
            stdin=subprocess.PIPE,  # Send password here
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
            print(f"BENCHMARK OUTPUT: {line.strip()}")
            socketio.emit("log_update_benchmark_tool", {"log": line.strip()})
            process.stdout.flush()

        for line in iter(process.stderr.readline, ""):
            print(f"BENCHMARK ERROR: {line.strip()}")
            socketio.emit("log_update_benchmark_tool", {"log": f"ERROR: {line.strip()}"})
            process.stderr.flush()

        process.stdout.close()
        process.stderr.close()
        process.wait()

        if process.returncode != 0:
            error_msg = f"⚠ ERROR: Benchmark tool exited with code {process.returncode}"
            print(error_msg)
            socketio.emit("log_update_benchmark_tool", {"log": error_msg})

    except Exception as e:
        error_msg = f"❌ Failed to execute benchmark tool: {e}"
        print(error_msg)
        socketio.emit("log_update_benchmark_tool", {"log": error_msg})

@app.route('/start-benchmark', methods=['POST'])
def start_benchmark():
    """ Starts the benchmark and logs streaming. """
    print("Received benchmark start request.")
    socketio.start_background_task(target=stream_benchmark_logs)
    return jsonify({"message": "Benchmark started, CLI logs streaming"}), 200

if __name__ == '__main__':
    print("Flask server starting on 127.0.0.1:5000...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
