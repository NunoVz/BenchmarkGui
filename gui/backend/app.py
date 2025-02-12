from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time

app = Flask(__name__)
CORS(app)

# Simulated benchmark status
benchmark_status = {"status": "idle", "progress": "0%", "results": {}}

def run_benchmark():
    global benchmark_status
    benchmark_status["status"] = "running"
    for i in range(1, 11):
        time.sleep(1)  # Simulate benchmark process
        benchmark_status["progress"] = f"{i*10}%"
    benchmark_status["status"] = "completed"
    benchmark_status["results"] = {"latency": "10ms", "throughput": "1Gbps"}

@app.route('/start-benchmark', methods=['POST'])
def start_benchmark():
    global benchmark_status
    if benchmark_status["status"] == "running":
        return jsonify({"message": "Benchmark already running!"}), 400
    thread = threading.Thread(target=run_benchmark)
    thread.start()
    return jsonify({"message": "Benchmark started!"}), 200

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(benchmark_status), 200

@app.route('/results', methods=['GET'])
def get_results():
    return jsonify(benchmark_status["results"]), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
