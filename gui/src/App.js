import React, { useState, useEffect } from "react";
import axios from "axios";
import { io } from "socket.io-client";

function BenchmarkDashboard() {
    const [toolLogs, setToolLogs] = useState([]);
    const [status, setStatus] = useState("idle");

    useEffect(() => {
        const socket = io("http://localhost:5000");  // Connect WebSocket

        // Listen for Benchmark CLI output
        socket.on("log_update_benchmark_tool", (data) => {
            setToolLogs((prevLogs) => [...prevLogs, data.log]);
        });

        return () => socket.disconnect();
    }, []);

    const startBenchmark = async () => {
        setToolLogs([]);
        setStatus("running");

        try {
            const response = await axios.post("/start-benchmark", { message: "Start requested from React" });
            console.log("Response from Flask:", response.data);
        } catch (error) {
            console.error("Error starting benchmark:", error);
        }
    };

    return (
        <div style={{ padding: "20px", textAlign: "center" }}>
            <h1>Benchmarking Dashboard</h1>
            <button onClick={startBenchmark} style={{ padding: "10px", fontSize: "16px" }}>Start Benchmark</button>
            
            <h2>Status: {status}</h2>

            {/* Benchmark Tool Logs */}
            <div style={{ maxHeight: "400px", overflowY: "auto", border: "1px solid #ccc", padding: "10px", marginTop: "20px", textAlign: "left" }}>
                <h3>Benchmark Tool CLI Output</h3>
                <pre style={{ whiteSpace: "pre-wrap" }}>{toolLogs.join("\n")}</pre>
            </div>
        </div>
    );
}

export default BenchmarkDashboard;
