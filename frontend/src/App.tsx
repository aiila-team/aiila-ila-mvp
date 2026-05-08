import { useEffect, useState } from "react";

function App() {

    const [alerts, setAlerts] = useState([]);

    useEffect(() => {

        // Connect to FastAPI WebSocket
        const ws = new WebSocket(
            "ws://localhost:8000/ws/alerts"
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
            console.log("WebSocket Closed");
        };

        // Cleanup
        return () => {
            ws.close();
        };

    }, []);

    // Send Alert API
    const sendAlert = async () => {

        try {

            const response = await fetch(
                "http://localhost:8000/api/send-alert",
                {
                    method: "POST"
                }
            );

            const data = await response.json();

            console.log(data);

        } catch (error) {

            console.log(
                "Error sending alert:",
                error
            );
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