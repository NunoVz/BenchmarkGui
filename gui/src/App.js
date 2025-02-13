import React, { useState, useEffect } from "react";
import axios from "axios";
import { io } from "socket.io-client";

function BenchmarkDashboard() {
    const [toolLogs, setToolLogs] = useState([]);

    useEffect(() => {
        const socket = io("http://localhost:5000", {
            transports: ["websocket"],  
        }); 

        // Listen for Benchmark CLI output
        socket.on("log_update_benchmark_tool", (data) => {
            console.log("Received log:", data.log);  // Debugging: Ensure logs are received
            setToolLogs((prevLogs) => [...prevLogs, data.log]);
        });

        return () => socket.disconnect();
    }, []);

    const startBenchmark = async () => {
        setToolLogs([]); // Clear previous logs

        try {
            const response = await axios.post("/start-benchmark", { message: "Start requested from React" });
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
