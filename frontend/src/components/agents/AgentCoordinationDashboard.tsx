/**
 * Agent Coordination Dashboard
 * Real-time visualization of band of agents executing consultation
 */
import React, { useState, useEffect } from 'react';
import io, { Socket } from 'socket.io-client';

interface AgentEventPayload {
  agent_type?: string;
  consensus_score?: number;
  risk_score?: number;
  level?: string;
  reason?: string;
  [key: string]: unknown;
}

interface AgentEvent {
  timestamp: string;
  agent: string;
  event: string;
}

interface DashboardState {
  events: AgentEvent[];
  consensusScore: number;
  riskScore: number;
  agentsCompleted: number;
  recommendations: string[];
  escalations: string[];
}

export default function AgentCoordinationDashboard({ consultationId }: { consultationId: string }) {
  const [state, setState] = useState<DashboardState>({
    events: [],
    consensusScore: 0,
    riskScore: 0,
    agentsCompleted: 0,
    recommendations: [],
    escalations: []
  });

  const [isRunning, setIsRunning] = useState(false);
  const [socket, setSocket] = useState<Socket | null>(null);

  // Initialize Socket.IO connection
  useEffect(() => {
    const newSocket = io(process.env.REACT_APP_API_URL || 'http://localhost:8000', {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5
    });

    // Join consultation room
    newSocket.emit('join_consultation', { consultation_id: consultationId });

    // Listen for agent events
    // Match backend event names exactly
    newSocket.on(`agent:agent_started`, (data: AgentEventPayload) => {
      addEvent(`${data.agent_type ?? 'Agent'} started analyzing`, data.agent_type ?? 'unknown');
    });

    newSocket.on(`agent:agent_completed`, (data: AgentEventPayload) => {
      addEvent(`${data.agent_type ?? 'Agent'} completed`, data.agent_type ?? 'unknown');
      setState(prev => ({
        ...prev,
        agentsCompleted: prev.agentsCompleted + 1
      }));
    });

    // Backend emits: agent:consensus_update (not consensus:updated)
    newSocket.on(`agent:consensus_update`, (data: AgentEventPayload) => {
      setState(prev => ({
        ...prev,
        consensusScore: data.consensus_score ?? prev.consensusScore,
        riskScore: data.risk_score ?? prev.riskScore,
        recommendations: Array.isArray(data.recommendations) ? data.recommendations as string[] : prev.recommendations
      }));
      addEvent('Consensus updated', 'System');
    });

    // Backend emits: agent:escalation_required (not agent:escalation)
    newSocket.on(`agent:escalation_required`, (data: AgentEventPayload) => {
      setState(prev => ({
        ...prev,
        escalations: [...prev.escalations, data.reason || 'Unknown escalation']
      }));
      addEvent('Escalation required', 'System');
    });

    setSocket(newSocket);

    return () => {
      newSocket.disconnect();
    };
  }, [consultationId]);

  const addEvent = (event: string, agent: string) => {
    setState(prev => ({
      ...prev,
      events: [...prev.events, {
        timestamp: new Date().toLocaleTimeString(),
        agent,
        event
      }].slice(-15) // Keep last 15 events
    }));
  };

  const startDemo = async () => {
    setIsRunning(true);
    setState({
      events: [{ timestamp: new Date().toLocaleTimeString(), agent: 'System', event: 'Starting demo...' }],
      consensusScore: 0,
      riskScore: 0,
      agentsCompleted: 0,
      recommendations: [],
      escalations: []
    });

    try {
      const response = await fetch('http://localhost:8000/api/demo/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const result = await response.json();
      
      if (result.status === 'COMPLETED') {
        setState(prev => ({
          ...prev,
          consensusScore: result.processing_report?.consensus_score || 0,
          riskScore: result.processing_report?.risk_score || 0,
          agentsCompleted: result.processing_report?.agents_executed?.length || 7,
          recommendations: result.processing_report?.recommendations?.map((r: { text?: string } | string) => (typeof r === "string" ? r : r.text || "")) || [],
          events: [
            ...prev.events,
            { timestamp: new Date().toLocaleTimeString(), agent: 'System', event: 'Demo completed successfully!' }
          ]
        }));
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        events: [...prev.events, { timestamp: new Date().toLocaleTimeString(), agent: 'System', event: `Error: ${error}` }]
      }));
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px', fontFamily: 'system-ui' }}>
      <h1 style={{ fontSize: '28px', marginBottom: '20px', color: '#333' }}>
        🏥 Band of Agents - Healthcare Coordination Dashboard
      </h1>

      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px', fontSize: '13px', color: '#555' }}>
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: socket?.connected ? '#22c55e' : '#ef4444',
            display: 'inline-block',
          }}
        />
        {socket?.connected ? 'Live updates connected' : 'Connecting to live updates…'}
      </div>
      
      <button 
        onClick={startDemo}
        disabled={isRunning}
        style={{
          padding: '12px 24px',
          fontSize: '16px',
          fontWeight: 'bold',
          backgroundColor: '#0066cc',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          marginBottom: '20px',
          cursor: isRunning ? 'not-allowed' : 'pointer',
          opacity: isRunning ? 0.6 : 1
        }}
      >
        {isRunning ? '⏳ Running Demo...' : '▶️ Run Agent Demo'}
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '20px' }}>
        {/* Agent Progress */}
        <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#333' }}>👥 Agent Execution</h3>
          <div style={{ width: '100%', height: '24px', backgroundColor: '#eee', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${(state.agentsCompleted / 7) * 100}%`,
              backgroundColor: '#0066cc',
              transition: 'width 0.3s ease'
            }} />
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '14px', color: '#666' }}>{state.agentsCompleted}/7 agents completed</p>
        </div>

        {/* Consensus Score */}
        <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#333' }}>✓ Consensus Score</h3>
          <div style={{ width: '100%', height: '24px', backgroundColor: '#eee', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${state.consensusScore * 100}%`,
              backgroundColor: '#44aa44',
              transition: 'width 0.3s ease'
            }} />
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '14px', color: '#666' }}>{(state.consensusScore * 100).toFixed(1)}%</p>
        </div>

        {/* Risk Assessment */}
        <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#333' }}>⚠️ Risk Level</h3>
          <div style={{
            padding: '12px',
            borderRadius: '4px',
            backgroundColor: state.riskScore > 0.7 ? '#ff4444' : state.riskScore > 0.4 ? '#ffaa00' : '#44aa44',
            color: 'white',
            textAlign: 'center',
            fontWeight: 'bold',
            fontSize: '18px'
          }}>
            {(state.riskScore * 100).toFixed(0)}%
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '14px', color: '#666', textAlign: 'center' }}>
            {state.riskScore > 0.7 ? '🔴 HIGH' : state.riskScore > 0.4 ? '🟡 MEDIUM' : '🟢 LOW'}
          </p>
        </div>
      </div>

      {/* Agent Activity Feed */}
      <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginBottom: '20px', maxHeight: '250px', overflow: 'auto' }}>
        <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#333' }}>📋 Agent Activity Feed</h3>
        {state.events.length === 0 ? (
          <p style={{ color: '#999', fontStyle: 'italic' }}>Waiting for agent activity...</p>
        ) : (
          state.events.map((event, idx) => (
            <div key={idx} style={{ padding: '8px', borderBottom: '1px solid #eee', fontSize: '13px', fontFamily: 'monospace' }}>
              <span style={{ color: '#999' }}>[{event.timestamp}]</span>
              {' '}
              <span style={{ color: '#0066cc', fontWeight: 'bold' }}>{event.agent}</span>
              {' '}
              <span>{event.event}</span>
            </div>
          ))
        )}
      </div>

      {/* Recommendations */}
      {state.recommendations.length > 0 && (
        <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#333' }}>💊 Recommendations</h3>
          <ul style={{ margin: '0', paddingLeft: '20px' }}>
            {state.recommendations.map((rec, idx) => (
              <li key={idx} style={{ marginBottom: '8px', color: '#555' }}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}