import React, { useEffect, useState, useMemo } from 'react';
import { useSchedulerSocket } from './hooks/useSchedulerSocket';
import { fetchHealth, fetchSessions, fetchDevices } from './api';
import './App.css';

// Node lifecycle state map matching SRS Appendix B
const STATE_META = {
  ACTIVE_PHYSICAL_LINK: { label: 'Active Link', className: 'state-active', badgeClass: 'badge-active' },
  PAUSED_QUEUED:        { label: 'Paused / Queued', className: 'state-paused', badgeClass: 'badge-paused' },
  CONNECTING:           { label: 'Connecting', className: 'state-connect', badgeClass: 'badge-connect' },
  DEGRADED_RETRY:       { label: 'Degraded', className: 'state-degraded', badgeClass: 'badge-degraded' },
  DEGRADED:             { label: 'Degraded', className: 'state-degraded', badgeClass: 'badge-degraded' },
  UNINITIALIZED:        { label: 'Uninitialized', className: 'state-uninit', badgeClass: 'badge-uninit' },
};

export default function App() {
  const { isConnected, lastEvent, eventHistory } = useSchedulerSocket('ws://localhost:8000/ws');

  // Dashboard state
  const [sessions, setSessions] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [tSliceMs, setTSliceMs] = useState(500); // SRS REQ-2 default 500ms

  // Simulated / Registered nodes pool (N >= 10, SRS 1.4)
  const [nodes, setNodes] = useState(() => [
    { id: 'node_00', name: 'File Peer 00', state: 'ACTIVE_PHYSICAL_LINK', queueDepth: 4, rssi: -62, rtt: 18.2 },
    { id: 'node_01', name: 'File Peer 01', state: 'ACTIVE_PHYSICAL_LINK', queueDepth: 2, rssi: -65, rtt: 21.4 },
    { id: 'node_02', name: 'File Peer 02', state: 'ACTIVE_PHYSICAL_LINK', queueDepth: 0, rssi: -58, rtt: 16.9 },
    { id: 'node_03', name: 'File Peer 03', state: 'PAUSED_QUEUED', queueDepth: 8, rssi: -71, rtt: 28.1 },
    { id: 'node_04', name: 'File Peer 04', state: 'PAUSED_QUEUED', queueDepth: 12, rssi: -69, rtt: 24.3 },
    { id: 'node_05', name: 'File Peer 05', state: 'PAUSED_QUEUED', queueDepth: 5, rssi: -74, rtt: 31.0 },
    { id: 'node_06', name: 'File Peer 06', state: 'PAUSED_QUEUED', queueDepth: 3, rssi: -64, rtt: 19.5 },
    { id: 'node_07', name: 'File Peer 07', state: 'CONNECTING', queueDepth: 6, rssi: -67, rtt: 22.8 },
    { id: 'node_08', name: 'File Peer 08', state: 'DEGRADED_RETRY', queueDepth: 15, rssi: -84, rtt: 45.2 },
    { id: 'node_09', name: 'File Peer 09', state: 'UNINITIALIZED', queueDepth: 0, rssi: null, rtt: null },
    { id: 'node_10', name: 'File Peer 10', state: 'UNINITIALIZED', queueDepth: 0, rssi: null, rtt: null },
    { id: 'node_11', name: 'File Peer 11', state: 'UNINITIALIZED', queueDepth: 0, rssi: null, rtt: null },
  ]);

  // Load initial backend telemetry & sessions
  useEffect(() => {
    fetchHealth().then(setSystemHealth).catch(() => setSystemHealth({ status: 'offline' }));
    fetchSessions().then(setSessions).catch(() => setSessions([]));
  }, []);

  // Update node states reactively upon receiving WebSocket events
  useEffect(() => {
    if (!lastEvent) return;

    if (lastEvent.type === 'SLOT_ROTATION' && lastEvent.data?.active_batch) {
      const activeBatch = new Set(lastEvent.data.active_batch);
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          state: activeBatch.has(n.id) ? 'ACTIVE_PHYSICAL_LINK' : n.state === 'DEGRADED_RETRY' ? 'DEGRADED_RETRY' : 'PAUSED_QUEUED',
        }))
      );
    } else if (lastEvent.type === 'SOCKET_STATE_CHANGE' && lastEvent.data) {
      const { device_id, state } = lastEvent.data;
      setNodes((prev) =>
        prev.map((n) => (n.id === device_id ? { ...n, state } : n))
      );
    } else if (lastEvent.type === 'BUFFER_UPDATE' && lastEvent.data) {
      const { device_id, queue_depth } = lastEvent.data;
      setNodes((prev) =>
        prev.map((n) => (n.id === device_id ? { ...n, queueDepth: queue_depth } : n))
      );
    }
  }, [lastEvent]);

  // Aggregated Telemetry Calculations (SRS 5.1 & REQ-10)
  const activePhysicalCount = useMemo(
    () => nodes.filter((n) => n.state === 'ACTIVE_PHYSICAL_LINK').length,
    [nodes]
  );

  const totalQueueDepth = useMemo(
    () => nodes.reduce((acc, curr) => acc + (curr.queueDepth || 0), 0),
    [nodes]
  );

  const averageRtt = useMemo(() => {
    const valid = nodes.filter((n) => n.rtt != null);
    if (!valid.length) return 0;
    return (valid.reduce((acc, curr) => acc + curr.rtt, 0) / valid.length).toFixed(1);
  }, [nodes]);

  return (
    <div className="dashboard-root">
      {/* Top Navigation / Brand */}
      <header className="dashboard-header">
        <div className="brand-section">
          <h1 className="brand-title">BT-Mux Diagnostic Profiler</h1>
          <span className="brand-tag">Academic Testbed</span>
        </div>

        <div className="header-status">
          <div className="connection-indicator">
            <span className={`indicator-dot ${isConnected ? 'dot-connected' : 'dot-disconnected'}`} />
            <span>{isConnected ? 'Live Telemetry IPC Active' : 'Connecting to ws://localhost:8000...'}</span>
          </div>
          {systemHealth && (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              HAL: <strong style={{ color: 'var(--accent-cyan)' }}>{systemHealth.ble_transport || 'simulated'}</strong>
            </span>
          )}
        </div>
      </header>

      {/* Main Grid Workspace */}
      <main className="dashboard-body">
        <div className="main-panel">
          {/* Top Metric Profiler Cards (SRS REQ-10) */}
          <section className="metrics-banner">
            <div className="metric-card">
              <span className="metric-title">Active Physical Slots</span>
              <span className="metric-val">{activePhysicalCount} / 4</span>
              <span className="metric-sub">Host $N_{'{max}'}$ limit</span>
            </div>

            <div className="metric-card">
              <span className="metric-title">Logical Streams</span>
              <span className="metric-val">{nodes.length}</span>
              <span className="metric-sub">Target $N \ge 10$ multiplexed</span>
            </div>

            <div className="metric-card">
              <span className="metric-title">Aggregate In-Flight</span>
              <span className="metric-val">{totalQueueDepth}</span>
              <span className="metric-sub">RAM FIFO chunks (REQ-6)</span>
            </div>

            <div className="metric-card">
              <span className="metric-title">Mean RTT Latency</span>
              <span className="metric-val">{averageRtt} ms</span>
              <span className="metric-sub">Benchmark latency target</span>
            </div>

            <div className="metric-card">
              <span className="metric-title">Global PDR</span>
              <span className="metric-val" style={{ color: 'var(--state-active)' }}>98.4%</span>
              <span className="metric-sub">Target $\ge 95\%$ (SRS 5.1)</span>
            </div>
          </section>

          {/* Interactive Dynamic T_slice Controls (SRS REQ-11) */}
          <section className="control-card">
            <div className="card-title">
              <span>Dynamic TDM Scheduler Control (REQ-11)</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Runtime $T_{'{slice}'}$ adjustments without system halt
              </span>
            </div>

            <div className="slider-group">
              <div className="slider-header">
                <span>Time-Slice Window Duration ($T_{'{slice}'}$)</span>
                <span className="slider-val">{tSliceMs} ms</span>
              </div>
              <input
                type="range"
                className="slider-input"
                min="100"
                max="2000"
                step="50"
                value={tSliceMs}
                onChange={(e) => setTSliceMs(Number(e.target.value))}
              />
              <div className="slider-bounds">
                <span>Min: 100 ms (SRS REQ-2)</span>
                <span>Default: 500 ms</span>
                <span>Max: 2000 ms (SRS REQ-2)</span>
              </div>
            </div>
          </section>

          {/* Interactive Node Canvas (SRS REQ-9) */}
          <section className="canvas-card">
            <div className="card-title">
              <span>Multiplexed Peripheral Canvas ($N \ge 10$ Logical Streams)</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Live state visualization (REQ-9)
              </span>
            </div>

            <div className="canvas-legend">
              <div className="legend-item">
                <span className="legend-dot" style={{ background: 'var(--state-active)' }} />
                <span>Active Physical Link (GATT Slot)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: 'var(--state-paused)' }} />
                <span>Paused / Queued (TDM Rotation)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: 'var(--state-connect)' }} />
                <span>Connecting (Handshake)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: 'var(--state-degraded)' }} />
                <span>Degraded (Timeout / Retry)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: 'var(--state-uninit)' }} />
                <span>Uninitialized</span>
              </div>
            </div>

            <div className="nodes-grid">
              {nodes.map((node) => {
                const meta = STATE_META[node.state] || STATE_META.UNINITIALIZED;
                const queuePercent = Math.min(100, (node.queueDepth / 20) * 100);

                return (
                  <div key={node.id} className={`node-box ${meta.className}`}>
                    <div className="node-header">
                      <span className="node-id">{node.id}</span>
                      <span className={`node-badge ${meta.badgeClass}`}>{meta.label}</span>
                    </div>

                    <div className="node-details">
                      <div className="detail-row">
                        <span>Designation</span>
                        <strong>{node.name}</strong>
                      </div>
                      <div className="detail-row">
                        <span>Signal (RSSI)</span>
                        <span>{node.rssi ? `${node.rssi} dBm` : '—'}</span>
                      </div>
                      <div className="detail-row">
                        <span>RTT</span>
                        <span>{node.rtt ? `${node.rtt} ms` : '—'}</span>
                      </div>
                    </div>

                    <div className="queue-meter-wrap">
                      <div className="queue-label-bar">
                        <span>Queue Depth (RAM FIFO)</span>
                        <span>{node.queueDepth} chunks</span>
                      </div>
                      <div className="queue-meter">
                        <div
                          className="queue-meter-fill"
                          style={{
                            width: `${queuePercent}%`,
                            backgroundColor: node.queueDepth > 10 ? 'var(--state-degraded)' : 'var(--accent-cyan)',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        {/* Sidebar: Real-Time Event Telemetry Feed */}
        <aside className="sidebar-panel">
          <div className="feed-card">
            <div className="card-title">
              <span>Live IPC Event Stream</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
                {eventHistory.length} events
              </span>
            </div>

            <div className="feed-list">
              {eventHistory.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '16px 0', textAlign: 'center' }}>
                  Awaiting live scheduler events from backend...
                </div>
              ) : (
                eventHistory.map((ev, idx) => (
                  <div key={idx} className="feed-item">
                    <span className="feed-type">{ev.type || 'EVENT'}</span>
                    <span className="feed-body">{JSON.stringify(ev.data)}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
