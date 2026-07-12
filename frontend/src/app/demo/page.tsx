"use client";

import AgentCoordinationDashboard from "@/components/agents/AgentCoordinationDashboard";

export default function DemoPage() {
  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#f5f5f5", padding: "20px" }}>
      <div style={{ maxWidth: "1400px", margin: "0 auto" }}>
        <h1 style={{ fontSize: "32px", marginBottom: "10px", color: "#333" }}>
         CareSyncAI - Multi-Agent Healthcare Coordination Demo
        </h1>
        <p style={{ color: "#666", marginBottom: "20px", fontSize: "16px" }}>
          Real-time multi-agent telemedicine consultation system. Watch 7 healthcare agents collaborate to analyze a patient case.
        </p>
        <AgentCoordinationDashboard consultationId="demo-001" />
      </div>
    </div>
  );
}