from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import subprocess
import os
import shlex

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# SUDO PASSWORD (Consider using sudoers instead)
SUDO_PASSWORD = "b1vbx11"

# Path to Benchmark Tool Directory
BENCHMARK_DIR = "/BenchmarkGui/Tese-2"
BENCHMARK_CMD = f"echo {SUDO_PASSWORD} | sudo -S python3 benchmark.py -ip 193.137.203.34 -p 6653 -s 12 -q 3 -max 30 -n onos -t 3-tier -m N"

def stream_benchmark_logs():
    """ Runs benchmark.py and streams output to React in real-time. """
    try:
        print(f"Changing directory to: {BENCHMARK_DIR}")
        os.chdir(BENCHMARK_DIR)  # Ensure correct working directory

        print(f"Executing: {BENCHMARK_CMD}")
        process = subprocess.Popen(
            shlex.split(BENCHMARK_CMD), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            bufsize=1  # Line buffering for real-time output
        )

        # Read stdout and stderr line by line
        for line in iter(process.stdout.readline, ""):
            print(f"BENCHMARK OUTPUT: {line.strip()}")  # Debugging
            socketio.emit("log_update_benchmark_tool", {"log": line.strip()})
            process.stdout.flush()

        for line in iter(process.stderr.readline, ""):
            print(f"BENCHMARK ERROR: {line.strip()}")  # Debugging
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
