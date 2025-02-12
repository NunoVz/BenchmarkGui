from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import shlex

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store benchmark status
benchmark_status = {"status": "idle", "progress": "0%", "logs": []}

def run_benchmark(command):
    """ Runs the benchmark command and streams logs to React. """
    global benchmark_status
    benchmark_status["status"] = "running"
    benchmark_status["logs"] = []

    # Start the process
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # Stream logs in real-time
    for line in iter(process.stdout.readline, ""):
        benchmark_status["logs"].append(line.strip())
        socketio.emit("log_update", {"log": line.strip()})  
        
    process.stdout.close()
    process.wait()

    # Update final status
    benchmark_status["status"] = "completed"
    socketio.emit("benchmark_done", {"status": "completed"})  # Notify React

@app.route('/start-benchmark', methods=['POST'])
def start_benchmark():
    """ Receives benchmark arguments from React and starts the process. """
    global benchmark_status
    if benchmark_status["status"] == "running":
        return jsonify({"message": "Benchmark already running!"}), 400

    data = request.json  # Get arguments from React

    # Build the benchmark command
    command = f"sudo python3 benchmark.py -ip {data['ip']} -p {data['port']} -s {data['start']} -q {data['query']} -max {data['max']} -n {data['controller']} -t {data['topology']} -m {data['metrics']}"
    
    # Start benchmark in a separate thread
    socketio.start_background_task(target=run_benchmark, command=command)
    
    return jsonify({"message": "Benchmark started!", "command": command}), 200

@app.route('/status', methods=['GET'])
def get_status():
    """ Returns the current benchmark status and logs. """
    return jsonify(benchmark_status), 200

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
