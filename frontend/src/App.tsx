// src/App.jsx

import { useEffect, useState } from "react";

function App() {

    const [alerts, setAlerts] = useState([]);
    const [socket, setSocket] = useState(null);

    useEffect(() => {

        // WebSocket Connection
        const ws = new WebSocket(
            "ws://localhost/ws/alerts"
        );

        ws.onopen = () => {
            console.log("WebSocket Connected");
        };

        ws.onmessage = (event) => {

            console.log("Received:", event.data);

            setAlerts((prev) => [
                event.data,
                ...prev
            ]);
        };

        ws.onerror = (error) => {
            console.log("WebSocket Error:", error);
        };

        ws.onclose = () => {
            console.log("WebSocket Disconnected");
        };

        setSocket(ws);

        // Cleanup
        return () => {
            ws.close();
        };

    }, []);

    // Send Alert API
    const sendAlert = async () => {

        try {

            await fetch(
                "/api/send-alert",
                {
                    method: "POST"
                }
            );

        } catch (error) {

            console.log("Error sending alert:", error);
        }
    };

    return (

        <div style={{ padding: "20px" }}>

            <h1>Real-Time Risk Alerts</h1>

            <button onClick={sendAlert}>
                Generate Alert
            </button>

            <ul>

                {alerts.map((alert, index) => (

                    <li key={index}>
                        {alert}
                    </li>

                ))}

            </ul>

        </div>
    );
}

export default App;