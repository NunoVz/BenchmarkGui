import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';

function BenchmarkDashboard() {
    const [status, setStatus] = useState({});
    const [results, setResults] = useState({});

    const startBenchmark = async () => {
        try {
            await axios.post('http://localhost:443/start-benchmark');
        } catch (error) {
            console.error("Error starting benchmark:", error);
        }
    };

    useEffect(() => {
        const interval = setInterval(async () => {
            const res = await axios.get('http://localhost:443/status');
            setStatus(res.data);

            if (res.data.status === "completed") {
                const resultRes = await axios.get('http://localhost:443/results');
                setResults(resultRes.data);
            }
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div style={{ padding: '20px', textAlign: 'center' }}>
            <h1>Benchmarking Dashboard</h1>
            <button onClick={startBenchmark} style={{ padding: '10px', fontSize: '16px' }}>Start Benchmark</button>
            <h2>Status: {status.status}</h2>
            <h3>Progress: {status.progress}</h3>

            {status.status === "completed" && (
                <div>
                    <h2>Results</h2>
                    <pre>{JSON.stringify(results, null, 2)}</pre>
                    <Line
                        data={{
                            labels: ["10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"],
                            datasets: [
                                {
                                    label: "Benchmark Progress",
                                    data: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                                    borderColor: "blue",
                                    fill: false,
                                },
                            ],
                        }}
                    />
                </div>
            )}
        </div>
    );
}

export default BenchmarkDashboard;
