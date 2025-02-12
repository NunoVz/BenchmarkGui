import React, { useState, useEffect } from "react";
import axios from "axios";
import { io } from "socket.io-client";

function BenchmarkDashboard() {
    const [status, setStatus] = useState("idle");
    const [logs, setLogs] = useState([]);
    const [form, setForm] = useState({
        ip: "193.137.203.34",
        port: 6653,
        start: 12,
        query: 3,
        max: 30,
        controller: "onos",
        topology: "3-tier",
        metrics: "N",
    });

    useEffect(() => {
        const socket = io("http://localhost:5000");  // Connect WebSocket

        // Listen for real-time logs
        socket.on("log_update", (data) => {
            setLogs((prevLogs) => [...prevLogs, data.log]);
        });

        // Listen for benchmark completion
        socket.on("benchmark_done", (data) => {
            setStatus("completed");
        });

        return () => socket.disconnect();
    }, []);

    const startBenchmark = async () => {
        setLogs([]); // Clear old logs
        setStatus("running");

        try {
            await axios.post("/start-benchmark", form);
        } catch (error) {
            console.error("Error starting benchmark:", error);
        }
    };

    const handleChange = (e) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    return (
        <div style={{ padding: "20px", textAlign: "center" }}>
            <h1>Benchmarking Dashboard</h1>

            {/* Benchmark Input Form */}
            <div>
                <label>IP: <input name="ip" value={form.ip} onChange={handleChange} /></label>
                <label>Port: <input name="port" type="number" value={form.port} onChange={handleChange} /></label>
                <label>Start: <input name="start" type="number" value={form.start} onChange={handleChange} /></label>
                <label>Query: <input name="query" type="number" value={form.query} onChange={handleChange} /></label>
                <label>Max: <input name="max" type="number" value={form.max} onChange={handleChange} /></label>
                <label>Controller:
                    <select name="controller" value={form.controller} onChange={handleChange}>
                        <option value="onos">ONOS</option>
                        <option value="ryu">RYU</option>
                        <option value="odl">ODL</option>
                    </select>
                </label>
                <label>Topology:
                    <select name="topology" value={form.topology} onChange={handleChange}>
                        <option value="3-tier">3-Tier</option>
                        <option value="star">Star</option>
                        <option value="mesh">Mesh</option>
                        <option value="leaf-spine">Leaf-Spine</option>
                    </select>
                </label>
                <label>Metrics:
                    <select name="metrics" value={form.metrics} onChange={handleChange}>
                        <option value="TDT">TDT - Topology Discovery Time</option>
                        <option value="N">N - Northbound Metrics</option>
                        <option value="NNP">NNP - Southbound Node-to-Node Metrics: Proactive</option>
                        <option value="NN">NN - Southbound Node-to-Node Metrics: Reactive</option>
                        <option value="P">P - Southbound Node-to-Controller: Proactive</option>
                        <option value="R">R - Southbound Node-to-Controller: Reactive</option>
                    </select>
                </label>
            </div>

            <button onClick={startBenchmark} style={{ padding: "10px", fontSize: "16px" }}>Start Benchmark</button>
            
            <h2>Status: {status}</h2>

            {/* Live Log Display */}
            <div style={{ maxHeight: "300px", overflowY: "auto", border: "1px solid #ccc", padding: "10px", marginTop: "20px", textAlign: "left" }}>
                <h3>Live Logs</h3>
                <pre style={{ whiteSpace: "pre-wrap" }}>{logs.join("\n")}</pre>
            </div>
        </div>
    );
}

export default BenchmarkDashboard;
