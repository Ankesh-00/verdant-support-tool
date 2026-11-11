import { useState } from "react";
import CustomerView from "./components/CustomerView.jsx";
import AgentView from "./components/AgentView.jsx";

// The top-level Customer/Agent switch. It's a test tool so we can play both
// sides of the conversation ourselves.
export default function App() {
  const [view, setView] = useState("customer");

  return (
    <>
      <div className="topbar">
        <div className="brand">
          Verdant &amp; Co <small>Support Tool</small>
        </div>
        <div className="toggle">
          <button
            className={view === "customer" ? "active" : ""}
            onClick={() => setView("customer")}
          >
            Customer
          </button>
          <button
            className={view === "agent" ? "active" : ""}
            onClick={() => setView("agent")}
          >
            Agent
          </button>
        </div>
      </div>
      <div className="container">
        {view === "customer" ? <CustomerView /> : <AgentView />}
      </div>
    </>
  );
}
