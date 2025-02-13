import React, { useState, useEffect } from "react";
import axios from "axios";
import { io } from "socket.io-client";

function BenchmarkDashboard() {
    const [toolLogs, setToolLogs] = useState([]);
    const [socket, setSocket] = useState(null);  // ✅ This will store the WebSocket connection

    useEffect(() => {
        const newSocket = io("http://10.3.3.114:5000", {
            transports: ["websocket", "polling"],
            reconnectionAttempts: 5,
            timeout: 20000
        });

        setSocket(newSocket);  // ✅ Now we correctly set the socket state

        // Listen for Benchmark CLI output
        newSocket.on("log_update_benchmark_tool", (data) => {
            console.log("Received log:", data.log);
            setToolLogs((prevLogs) => [...prevLogs, data.log]);
        });

        // Listen for "benchmark_complete" and disconnect WebSocket
        newSocket.on("benchmark_complete", (data) => {
            console.log("Benchmark completed:", data.message);
            newSocket.disconnect();
        });

        return () => newSocket.disconnect();
    }, []);

    const startBenchmark = async () => {
        setToolLogs([]);

        try {
            const response = await axios.post("http://10.3.3.114:5000/start-benchmark", { message: "Start requested from React" });
            console.log("Response from Flask:", response.data);
        } catch (error) {
            console.error("Error starting benchmark:", error);
        }
    };

    return (
        <div style={{ padding: "20px", textAlign: "center" }}>
            <h1>Benchmarking CLI Output</h1>
            <button onClick={startBenchmark} style={{ padding: "10px", fontSize: "16px" }}>Start Benchmark</button>

            {/* CLI Output Display */}
            <div style={{
                maxHeight: "400px",
                overflowY: "auto",
                border: "1px solid #ccc",
                padding: "10px",
                marginTop: "20px",
                textAlign: "left",
                backgroundColor: "#000",
                color: "#0f0",
                fontFamily: "monospace"
            }}>
                <h3>Framework CLI Output</h3>
                <pre style={{ whiteSpace: "pre-wrap" }}>{toolLogs.join("\n")}</pre>
            </div>
        </div>
    );
}

export default BenchmarkDashboard;
