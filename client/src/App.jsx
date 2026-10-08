import React, { useEffect, useState, useMemo } from 'react';
import { useSchedulerSocket } from './hooks/useSchedulerSocket';
import {
  fetchHealth,
  fetchSimulationStatus,
  startSimulation,
  stopSimulation,
  updateTSlice,
  injectFault,
  clearAllFaults,
  enqueueTestChunks,
  resetSimulation,
  fetchMode,
  switchMode,
  scanPhysicalDevices,
  pairNodeToScheduler,
  unpairNodeFromScheduler,
  testConnect,
  transferFile,
  fetchTransfers,
} from './api';
import './App.css';

// Node lifecycle state map matching SRS and UI states
const STATE_META = {
  ACTIVE_PHYSICAL_LINK: { label: 'ACTIVE', className: 'state-active', badgeClass: 'badge-active' },
  ACTIVE:               { label: 'ACTIVE', className: 'state-active', badgeClass: 'badge-active' },
  PAUSED_QUEUED:        { label: 'PAUSED / QUEUED', className: 'state-paused', badgeClass: 'badge-paused' },
  PAUSED:               { label: 'PAUSED / QUEUED', className: 'state-paused', badgeClass: 'badge-paused' },
  CONNECTING:           { label: 'CONNECTING', className: 'state-connect', badgeClass: 'badge-connect' },
  DEGRADED_RETRY:       { label: 'DEGRADED / TIMEOUT', className: 'state-degraded', badgeClass: 'badge-degraded' },
  DEGRADED:             { label: 'DEGRADED / TIMEOUT', className: 'state-degraded', badgeClass: 'badge-degraded' },
  UNINITIALIZED:        { label: 'UNINITIALIZED', className: 'state-uninit', badgeClass: 'badge-uninit' },
};

function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function getRssiQuality(rssi) {
  if (rssi >= -55) return { percent: 100, color: '#5dcaa5', label: 'Excellent' };
  if (rssi >= -68) return { percent: 75, color: '#38bdf8', label: 'Good' };
  if (rssi >= -80) return { percent: 45, color: '#f59e0b', label: 'Fair' };
  return { percent: 20, color: '#f0997b', label: 'Weak' };
}

export default function App() {
  const { isConnected, lastEvent, eventHistory, sendMessage, clearEvents } = useSchedulerSocket('ws://localhost:8000/ws');

  // Navigation tab state: 'FILES' | 'BLUETOOTH'
  const [activeTab, setActiveTab] = useState('FILES');

  // Transport Mode: 'simulated' | 'physical'
  const [transportMode, setTransportMode] = useState('simulated');
  const [transportName, setTransportName] = useState('Simulated BLE (Virtual Demo)');

  // Physical Bluetooth Scanner state
  const [physicalDiscovered, setPhysicalDiscovered] = useState([]);
  const [isPhysicalScanning, setIsPhysicalScanning] = useState(false);
  const [deviceFilter, setDeviceFilter] = useState('');
  const [hideUnnamed, setHideUnnamed] = useState(true);
  const [manualMac, setManualMac] = useState('');
  const [manualName, setManualName] = useState('');
  const [testingDevice, setTestingDevice] = useState(null);
  const [testResultMap, setTestResultMap] = useState({});

  // Scheduler state
  const [isSchedulerRunning, setIsSchedulerRunning] = useState(true);
  const [tSliceMs, setTSliceMs] = useState(500);
  const [rotationCount, setRotationCount] = useState(0);
  const [alertMsg, setAlertMsg] = useState(null);
  const [showDebugStream, setShowDebugStream] = useState(false);

  // File Transfer State
  const [fileTransfers, setFileTransfers] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedRecipient, setSelectedRecipient] = useState('all');
  const [isSendingFile, setIsSendingFile] = useState(false);

  // Active batch (4 physical slots) & queued backlog
  const [activeBatch, setActiveBatch] = useState(['node_00', 'node_01', 'node_02', 'node_03']);
  const [queuedBatch, setQueuedBatch] = useState([
    'node_04', 'node_05', 'node_06', 'node_07', 'node_08', 'node_09', 'node_10', 'node_11',
  ]);

  // Track ACKed chunks per logical device
  const [ackedChunksMap, setAckedChunksMap] = useState({
    node_00: 16, node_01: 14, node_02: 18, node_03: 12,
    node_04: 9, node_05: 8, node_06: 11, node_07: 7,
    node_08: 4, node_09: 10, node_10: 8, node_11: 6,
  });

  // Feed filter for debug console
  const [feedFilter, setFeedFilter] = useState('ALL');

  // Active nodes pool (N >= 10)
  const [nodes, setNodes] = useState(() => [
    { id: 'node_00', name: 'File Peer 00', state: 'ACTIVE_PHYSICAL_LINK', queueDepth: 2, rssi: -58, rtt: 18.2, is_physical: false },
    { id: 'node_01', name: 'File Peer 01', state: 'ACTIVE_PHYSICAL_LINK', queueDepth: 1, rssi: -62, rtt: 21.4, is_physical: false },
    { id: 'node_02', name: 'File Peer 02', state: 'ACTIVE_PHYSICAL_LINK', queueDepth: 0, rssi: -55, rtt: 16.9, is_physical: false },
    { id: 'node_03', name: 'File Peer 03', state: 'ACTIVE_PHYSICAL_LINK', queueDepth: 3, rssi: -68, rtt: 24.3, is_physical: false },
    { id: 'node_04', name: 'File Peer 04', state: 'PAUSED_QUEUED', queueDepth: 4, rssi: -64, rtt: 19.5, is_physical: false },
    { id: 'node_05', name: 'File Peer 05', state: 'PAUSED_QUEUED', queueDepth: 2, rssi: -71, rtt: 26.0, is_physical: false },
    { id: 'node_06', name: 'File Peer 06', state: 'PAUSED_QUEUED', queueDepth: 3, rssi: -60, rtt: 17.8, is_physical: false },
    { id: 'node_07', name: 'File Peer 07', state: 'PAUSED_QUEUED', queueDepth: 1, rssi: -66, rtt: 22.1, is_physical: false },
    { id: 'node_08', name: 'File Peer 08', state: 'DEGRADED_RETRY', queueDepth: 5, rssi: -82, rtt: 42.0, is_physical: false },
    { id: 'node_09', name: 'File Peer 09', state: 'PAUSED_QUEUED', queueDepth: 0, rssi: -63, rtt: 20.4, is_physical: false },
    { id: 'node_10', name: 'File Peer 10', state: 'PAUSED_QUEUED', queueDepth: 0, rssi: -59, rtt: 19.1, is_physical: false },
    { id: 'node_11', name: 'File Peer 11', state: 'PAUSED_QUEUED', queueDepth: 0, rssi: -67, rtt: 23.5, is_physical: false },
  ]);

  // Load initial backend telemetry & transfers
  const refreshBackendData = () => {
    fetchMode().then((m) => {
      if (m) {
        setTransportMode(m.mode);
        setTransportName(m.transport_name);
      }
    }).catch(() => {});
    fetchSimulationStatus().then((status) => {
      if (status) {
        if (status.nodes) setNodes(status.nodes);
        if (status.mode) setTransportMode(status.mode);
        if (status.transport_name) setTransportName(status.transport_name);
        if (status.is_running !== undefined) setIsSchedulerRunning(status.is_running);
        if (status.t_slice_ms !== undefined) setTSliceMs(status.t_slice_ms);
      }
    }).catch(() => {});
    fetchTransfers().then((res) => {
      if (res?.transfers) setFileTransfers(res.transfers);
    }).catch(() => {});
  };

  useEffect(() => {
    refreshBackendData();
  }, []);

  const showAlert = (msg) => {
    setAlertMsg(msg);
    setTimeout(() => setAlertMsg(null), 4000);
  };

  // Process Real-time WebSocket Events
  useEffect(() => {
    if (!lastEvent) return;

    if (lastEvent.type === 'SLOT_ROTATION' && lastEvent.data) {
      if (lastEvent.data.active_batch) setActiveBatch(lastEvent.data.active_batch);
      if (lastEvent.data.queued_batch) setQueuedBatch(lastEvent.data.queued_batch);
      if (lastEvent.data.rotation_count !== undefined) setRotationCount(lastEvent.data.rotation_count);
      if (lastEvent.data.t_slice_ms !== undefined) setTSliceMs(lastEvent.data.t_slice_ms);
    } else if (lastEvent.type === 'SOCKET_STATE_CHANGE' && lastEvent.data) {
      const { device_id, state } = lastEvent.data;
      setNodes((prev) => prev.map((n) => (n.id === device_id ? { ...n, state } : n)));
    } else if (lastEvent.type === 'BUFFER_UPDATE' && lastEvent.data) {
      const { device_id, queue_depth } = lastEvent.data;
      setNodes((prev) => prev.map((n) => (n.id === device_id ? { ...n, queueDepth: queue_depth } : n)));
    } else if (lastEvent.type === 'CHUNK_EVENT' && lastEvent.data?.device_id) {
      const devId = lastEvent.data.device_id;
      setAckedChunksMap((prev) => ({ ...prev, [devId]: (prev[devId] || 0) + 1 }));
    } else if (lastEvent.type === 'FILE_TRANSFER_START' && lastEvent.data) {
      setFileTransfers((prev) => [lastEvent.data, ...prev.filter((t) => t.id !== lastEvent.data.id)]);
    } else if (lastEvent.type === 'FILE_TRANSFER_PROGRESS' && lastEvent.data) {
      setFileTransfers((prev) =>
        prev.map((t) => (t.id === lastEvent.data.id ? { ...t, ...lastEvent.data } : t))
      );
    } else if (lastEvent.type === 'CONFIG_UPDATE' && lastEvent.data?.t_slice_ms) {
      setTSliceMs(lastEvent.data.t_slice_ms);
    } else if (lastEvent.type === 'TELEMETRY_SNAPSHOT' && lastEvent.data) {
      const snap = lastEvent.data;
      if (snap.nodes) setNodes(snap.nodes);
      if (snap.rotation_count !== undefined) setRotationCount(snap.rotation_count);
      if (snap.is_running !== undefined) setIsSchedulerRunning(snap.is_running);
      if (snap.t_slice_ms !== undefined) setTSliceMs(snap.t_slice_ms);
      if (snap.mode) setTransportMode(snap.mode);
      if (snap.transport_name) setTransportName(snap.transport_name);
    } else if (lastEvent.type === 'MODE_CHANGED' && lastEvent.data) {
      setTransportMode(lastEvent.data.mode);
      setTransportName(lastEvent.data.transport_name);
    }
  }, [lastEvent]);

  // Mode switcher handler: 'physical' vs 'simulated'
  const handleModeSwitch = async (targetMode) => {
    try {
      const res = await switchMode(targetMode);
      setTransportMode(res.mode);
      setTransportName(res.transport_name);
      if (res.nodes) setNodes(res.nodes);
      showAlert(`Switched to ${res.mode.toUpperCase()} Mode: ${res.transport_name}`);
      if (targetMode === 'physical') {
        handleScanPhysical();
      }
    } catch (e) {
      showAlert(`Mode switch failed: ${e.message}`);
    }
  };

  // Scan real physical Bluetooth devices using Bleak
  const handleScanPhysical = async () => {
    setIsPhysicalScanning(true);
    showAlert('Scanning Bluetooth spectrum via WinRT radio...');
    try {
      const res = await scanPhysicalDevices();
      const devs = res.devices || [];
      setPhysicalDiscovered(devs);
      showAlert(`Discovered ${devs.length} real Bluetooth devices in range!`);
    } catch (e) {
      showAlert(`Physical BLE scan error: ${e.message}`);
    } finally {
      setIsPhysicalScanning(false);
    }
  };

  // Pair a physical Bluetooth peripheral into TDM Scheduler
  const handlePairPhysical = async (dev) => {
    try {
      const res = await pairNodeToScheduler({
        device_id: dev.device_id,
        name: dev.name || 'BLE Peripheral',
        rssi: dev.rssi || -60,
      });
      if (res.nodes) setNodes(res.nodes);
      showAlert(`Added real device ${dev.name} (${dev.device_id}) as file peer!`);
    } catch (e) {
      showAlert(`Pairing error: ${e.message}`);
    }
  };

  // Unpair device from TDM Scheduler
  const handleUnpairNode = async (deviceId) => {
    try {
      const res = await unpairNodeFromScheduler(deviceId);
      if (res.nodes) setNodes(res.nodes);
      showAlert(`Removed device ${deviceId} from file peers.`);
    } catch (e) {
      showAlert(`Unpair error: ${e.message}`);
    }
  };

  // Manual MAC address pair
  const handleManualPair = async (e) => {
    e.preventDefault();
    if (!manualMac.trim()) return;
    await handlePairPhysical({
      device_id: manualMac.trim(),
      name: manualName.trim() || 'Physical BLE Peripheral',
      rssi: -65,
    });
    setManualMac('');
    setManualName('');
  };

  // Test physical GATT link connectivity
  const handleTestConnect = async (dev) => {
    setTestingDevice(dev.device_id);
    try {
      const res = await testConnect({
        device_id: dev.device_id,
        name: dev.name || 'BLE Peripheral',
        rssi: dev.rssi || -60,
      });
      setTestResultMap((prev) => ({ ...prev, [dev.device_id]: res }));
      if (res.success) {
        showAlert(`✓ Connection test passed for ${dev.name}! Found ${res.services_count} GATT services.`);
      } else {
        showAlert(`ℹ ${res.message}`);
      }
    } catch (e) {
      setTestResultMap((prev) => ({
        ...prev,
        [dev.device_id]: { success: false, message: e.message },
      }));
      showAlert(`Connection test error: ${e.message}`);
    } finally {
      setTestingDevice(null);
    }
  };

  // Quick-add top scanned devices into multiplexer
  const handleQuickAddAll = async () => {
    const sourceList = hideUnnamed
      ? physicalDiscovered.filter((d) => d.name && d.name !== 'Unknown BLE Peripheral' && d.name !== 'Unknown BLE Device' && d.has_name !== false)
      : physicalDiscovered;

    if (!sourceList.length) {
      showAlert('No named devices found. Run "Scan Bluetooth Devices" first.');
      return;
    }
    const toAdd = sourceList.slice(0, 12);
    for (const dev of toAdd) {
      await handlePairPhysical(dev);
    }
    showAlert(`Added ${toAdd.length} named BLE devices as file peers!`);
  };

  // Dynamic T_slice update handler
  const handleTSliceChange = async (val) => {
    setTSliceMs(val);
    try {
      await updateTSlice(val);
      showAlert(`Slot duration updated to ${val} ms`);
    } catch {
      sendMessage({ command: 'SET_T_SLICE', value: val });
    }
  };

  // Toggle scheduler running state
  const toggleScheduler = async () => {
    if (isSchedulerRunning) {
      await stopSimulation();
      setIsSchedulerRunning(false);
      showAlert('Multiplexed file transfer paused.');
    } else {
      await startSimulation();
      setIsSchedulerRunning(true);
      showAlert('Multiplexed file transfer resumed.');
    }
  };

  // Fault injection handler
  const handleFaultInjection = async (nodeId, type) => {
    try {
      await injectFault(nodeId, type);
      showAlert(`Node ${nodeId} transitioned to ${type === 'degrade' ? 'DEGRADED_RETRY (Timeout)' : 'RESTORED'}`);
    } catch (e) {
      showAlert(`Fault injection failed: ${e.message}`);
    }
  };

  // Clear all faults
  const handleClearFaults = async () => {
    await clearAllFaults();
    showAlert('All peer link timeouts cleared. Peers restored to queue.');
  };

  // Enqueue test chunks
  const handleEnqueue = async (nodeId, chunks = 4) => {
    await enqueueTestChunks(nodeId, chunks);
    showAlert(`Enqueued ${chunks} file chunks into ${nodeId} buffer.`);
  };

  // Reset entire simulation
  const handleReset = async () => {
    await resetSimulation();
    refreshBackendData();
    showAlert('System reset: queues flushed, buffers cleared, transfers reset.');
  };

  // File Transfer handlers
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile({
        name: file.name,
        size: file.size,
        type: file.type || 'application/octet-stream',
      });
    }
  };

  const handlePickSampleFile = (name, sizeBytes) => {
    setSelectedFile({
      name,
      size: sizeBytes,
      type: 'sample/file',
    });
  };

  const handleSendFile = async () => {
    if (!selectedFile) {
      showAlert('Please choose or select a file to transfer first.');
      return;
    }
    const recipients = selectedRecipient === 'all' ? ['all'] : [selectedRecipient];
    try {
      setIsSendingFile(true);
      const res = await transferFile({
        filename: selectedFile.name,
        size_bytes: selectedFile.size,
        recipient_ids: recipients,
        chunk_size: 240,
      });
      setFileTransfers((prev) => [res, ...prev.filter((t) => t.id !== res.id)]);
      showAlert(`Transfer started: "${selectedFile.name}" multiplexing across ${res.recipients.length} file peer(s).`);
      setSelectedFile(null);
    } catch (e) {
      showAlert(`File transfer error: ${e.message}`);
    } finally {
      setIsSendingFile(false);
    }
  };

  // Filtered event history for debug drawer
  const filteredEvents = useMemo(() => {
    if (feedFilter === 'ALL') return eventHistory;
    return eventHistory.filter((ev) => {
      if (feedFilter === 'ROTATIONS') return ev.type === 'SLOT_ROTATION';
      if (feedFilter === 'BUFFERS') return ev.type === 'BUFFER_UPDATE';
      if (feedFilter === 'CHUNKS') return ev.type === 'CHUNK_EVENT';
      return true;
    });
  }, [eventHistory, feedFilter]);

  // Telemetry Aggregates
  const activeNodes = useMemo(
    () => nodes.filter((n) => n.state === 'ACTIVE_PHYSICAL_LINK'),
    [nodes]
  );
  const activePhysicalCount = activeNodes.length;

  const totalQueueDepth = useMemo(
    () => nodes.reduce((acc, curr) => acc + (curr.queueDepth || 0), 0),
    [nodes]
  );

  const averageRtt = useMemo(() => {
    const valid = nodes.filter((n) => n.rtt != null);
    if (!valid.length) return 0;
    return (valid.reduce((acc, curr) => acc + curr.rtt, 0) / valid.length).toFixed(1);
  }, [nodes]);

  const activeNodeIds = useMemo(() => new Set(nodes.map((n) => n.id)), [nodes]);

  // Count of genuine named devices
  const namedCount = useMemo(() => {
    return physicalDiscovered.filter(
      (d) => d.name && d.name !== 'Unknown BLE Peripheral' && d.name !== 'Unknown BLE Device' && d.has_name !== false
    ).length;
  }, [physicalDiscovered]);

  // Filter discovered devices by named toggle and search input
  const filteredDiscovered = useMemo(() => {
    let list = physicalDiscovered;
    if (hideUnnamed) {
      list = list.filter(
        (d) => d.name && d.name !== 'Unknown BLE Peripheral' && d.name !== 'Unknown BLE Device' && d.has_name !== false
      );
    }
    if (deviceFilter.trim()) {
      const q = deviceFilter.toLowerCase();
      list = list.filter(
        (d) =>
          (d.name && d.name.toLowerCase().includes(q)) ||
          (d.device_id && d.device_id.toLowerCase().includes(q))
      );
    }
    return list;
  }, [physicalDiscovered, hideUnnamed, deviceFilter]);

  return (
    <div className="dashboard-container">
      {/* Top Banner / System Header */}
      <header className="dashboard-header">
        <div className="brand-section">
          <h1 className="brand-title">
            <span>📂</span> BT-Mux File Share
          </h1>
          <div className="connection-indicator">
            <span className={`indicator-dot ${isConnected ? 'dot-connected' : 'dot-disconnected'}`} />
            <span>{isConnected ? 'Live' : 'Offline'}</span>
          </div>
        </div>

        <div className="header-status">
          <div className="mode-toggle-group">
            <button
              className={`mode-toggle-btn ${transportMode === 'simulated' ? 'active mode-simulated' : ''}`}
              onClick={() => handleModeSwitch('simulated')}
            >
              🧪 Simulated
            </button>
            <button
              className={`mode-toggle-btn ${transportMode === 'physical' ? 'active mode-physical' : ''}`}
              onClick={() => handleModeSwitch('physical')}
            >
              📶 Physical BLE
            </button>
          </div>
          <button
            className={`btn btn-sm ${isSchedulerRunning ? 'btn-secondary' : 'btn-success'}`}
            onClick={toggleScheduler}
          >
            {isSchedulerRunning ? '⏸ Pause' : '▶ Start'}
          </button>
          <button className="btn btn-sm btn-outline" onClick={handleReset}>↺ Reset</button>
          <button
            className={`btn btn-sm btn-outline ${showDebugStream ? 'btn-active-debug' : ''}`}
            onClick={() => setShowDebugStream(!showDebugStream)}
            style={{ position: 'relative' }}
          >
            🛠️ Logs
            {filteredEvents.length > 0 && (
              <span className="debug-badge">{filteredEvents.length}</span>
            )}
          </button>
        </div>
      </header>

      {/* Nav Tabs Bar */}
      <nav className="nav-tabs-bar">
        {[
          { key: 'FILES', label: '📁 File Transfer & Dashboard' },
          { key: 'BLUETOOTH', label: `📡 BLE Device Scanner (${physicalDiscovered.length ? `${physicalDiscovered.length} Found` : 'Ready'})` },
        ].map((tab) => (
          <button
            key={tab.key}
            className={`nav-tab-btn ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Main Grid Workspace */}
      <main className="dashboard-body">
        <div className="main-panel">
          {/* Transient Alert Banner */}
          {alertMsg && (
            <div className="alert-banner alert-success">
              <span>{alertMsg}</span>
              <button
                onClick={() => setAlertMsg(null)}
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
          )}

          {/* Architecture Summary */}
          <div className="arch-summary">
            <span className="arch-flow">
              <strong>{nodes.length}</strong> file peers
              <span className="arch-arrow">→</span>
              chunk buffers ({totalQueueDepth} queued)
              <span className="arch-arrow">→</span>
              TDM scheduler ({tSliceMs}ms)
              <span className="arch-arrow">→</span>
              <strong>4</strong> radio slots
            </span>
          </div>

          {/* Key Metrics */}
          <section className="metrics-banner">
            <div className="metric-card">
              <span className="metric-title">Slots Used</span>
              <span className="metric-val">{activePhysicalCount}<span className="metric-of">/4</span></span>
            </div>
            <div className="metric-card">
              <span className="metric-title">File Peers</span>
              <span className="metric-val">{nodes.length}</span>
            </div>
            <div className="metric-card">
              <span className="metric-title">Rotations</span>
              <span className="metric-val">{rotationCount}</span>
            </div>
            <div className="metric-card">
              <span className="metric-title">Slot Time</span>
              <span className="metric-val" style={{ color: 'var(--accent-cyan)' }}>{tSliceMs}<span className="metric-unit">ms</span></span>
            </div>
            <div className="metric-card">
              <span className="metric-title">Avg Latency</span>
              <span className="metric-val">{averageRtt}<span className="metric-unit">ms</span></span>
            </div>
          </section>

          {/* TAB 1: FILE TRANSFER & DASHBOARD */}
          {activeTab === 'FILES' && (
            <>
              {/* File Transfer Center */}
              <section className="file-transfer-section">
                <div className="card-title-simple">
                  <span>📂 BLE File Transfer Center</span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>
                    Multiplexed Concurrent File Delivery
                  </span>
                </div>

                <div className="file-transfer-grid">
                  {/* Left Column: Send File */}
                  <div>
                    <h3 style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '8px' }}>
                      Select File to Send
                    </h3>

                    <label className="file-dropzone" htmlFor="file-input-upload">
                      <input
                        id="file-input-upload"
                        type="file"
                        style={{ display: 'none' }}
                        onChange={handleFileSelect}
                      />
                      <div className="file-dropzone-icon">📤</div>
                      <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        Click to Choose File or Drag & Drop
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        Supports PDF, images, docs, logs, or binaries (auto-chunked @ 240B)
                      </div>
                    </label>

                    {selectedFile && (
                      <div className="file-selected-box">
                        <div>
                          <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                            📄 {selectedFile.name}
                          </strong>
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                            {formatBytes(selectedFile.size)} · {Math.max(1, Math.ceil(selectedFile.size / 240))} BLE Chunks
                          </div>
                        </div>
                        <button
                          className="btn btn-sm btn-outline"
                          onClick={() => setSelectedFile(null)}
                        >
                          ✕ Clear
                        </button>
                      </div>
                    )}

                    <div style={{ marginTop: '12px' }}>
                      <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Or pick a sample file:</span>
                      <div className="sample-files-row">
                        <button
                          className="sample-file-chip"
                          onClick={() => handlePickSampleFile('Firmware_Update_v2.bin', 48 * 1024)}
                        >
                          ⚙️ Firmware (48 KB)
                        </button>
                        <button
                          className="sample-file-chip"
                          onClick={() => handlePickSampleFile('Project_Summary.pdf', 24 * 1024)}
                        >
                          📄 Report.pdf (24 KB)
                        </button>
                        <button
                          className="sample-file-chip"
                          onClick={() => handlePickSampleFile('Sensor_Capture.jpg', 64 * 1024)}
                        >
                          📷 Image.jpg (64 KB)
                        </button>
                      </div>
                    </div>

                    <div style={{ marginTop: '16px' }}>
                      <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                        Recipient Peer:
                      </label>
                      <select
                        className="config-input"
                        style={{ width: '100%', marginBottom: '12px' }}
                        value={selectedRecipient}
                        onChange={(e) => setSelectedRecipient(e.target.value)}
                      >
                        <option value="all">📡 All File Peers (Multicast to {nodes.length} nodes)</option>
                        {nodes.map((n) => (
                          <option key={n.id} value={n.id}>
                            {n.name} ({n.id}) {n.is_physical ? '[Physical]' : ''}
                          </option>
                        ))}
                      </select>

                      <button
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '10px' }}
                        onClick={handleSendFile}
                        disabled={!selectedFile || isSendingFile}
                      >
                        {isSendingFile ? '⏳ Enqueueing Chunks...' : '🚀 Send File via Multiplexer'}
                      </button>
                    </div>
                  </div>

                  {/* Right Column: Active & Recent Transfers */}
                  <div>
                    <h3 style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '8px' }}>
                      Transfer Queue & History ({fileTransfers.length})
                    </h3>

                    {fileTransfers.length === 0 ? (
                      <div style={{ background: 'var(--bg-surface)', padding: '32px 16px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '1.8rem', marginBottom: '8px' }}>📂</div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: 0 }}>
                          No file transfers yet. Select a file on the left and click "Send File" to watch TDM chunk multiplexing in real time.
                        </p>
                      </div>
                    ) : (
                      <div className="transfer-list">
                        {fileTransfers.map((tx) => {
                          const percent = tx.total_chunks > 0 ? Math.min(100, Math.round((tx.chunks_acked / tx.total_chunks) * 100)) : 0;
                          const isDone = tx.status === 'COMPLETED' || percent >= 100;

                          return (
                            <div key={tx.id} className={`transfer-item ${isDone ? 'completed' : ''}`}>
                              <div className="transfer-item-header">
                                <span className="transfer-filename">
                                  {isDone ? '✓' : '🔄'} {tx.filename}
                                </span>
                                <span
                                  className={`node-badge ${isDone ? 'badge-physical' : 'badge-active'}`}
                                  style={{ fontSize: '0.7rem' }}
                                >
                                  {isDone ? 'Completed' : `${percent}%`}
                                </span>
                              </div>

                              <div className="progress-bar-track">
                                <div
                                  className={`progress-bar-fill ${isDone ? 'done' : ''}`}
                                  style={{ width: `${percent}%` }}
                                />
                              </div>

                              <div className="transfer-meta-row">
                                <span>
                                  {formatBytes(tx.size_bytes)} · {tx.chunks_acked}/{tx.total_chunks} Chunks
                                </span>
                                <span>
                                  {tx.speed_kbps > 0 ? `${tx.speed_kbps} KB/s · ` : ''}
                                  {tx.recipients?.length === 1 ? `Peer: ${tx.recipient_names?.[0] || tx.recipients[0]}` : `To ${tx.recipients?.length || 0} Peers`}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </section>

              {/* Radio Slots — 4 Hardware GATT Channels */}
              <section className="radio-slots-card">
                <div className="card-title-simple">
                  <span>Radio Slots (4 Physical GATT Channels)</span>
                  <span className={`status-dot ${isSchedulerRunning ? 'live' : 'paused'}`}>
                    {isSchedulerRunning ? '● Running' : '○ Paused'}
                  </span>
                </div>

                <div className="radio-slots-grid">
                  {[0, 1, 2, 3].map((slotIdx) => {
                    const activeNodeId = activeBatch[slotIdx];
                    const dev = activeNodeId
                      ? nodes.find((n) => n.id === activeNodeId) || { id: activeNodeId, name: activeNodeId, queueDepth: 0, rssi: -60, rtt: 20 }
                      : null;

                    return (
                      <div key={slotIdx} className={`radio-slot-box ${dev ? 'slot-active' : 'slot-idle'}`}>
                        <span className="slot-channel-tag">Slot {slotIdx + 1}</span>
                        {dev ? (
                          <>
                            <span className="slot-device-name">{dev.name}</span>
                            <span className="slot-device-meta">{dev.rssi} dBm · {dev.rtt} ms · {dev.queueDepth} chunks</span>
                          </>
                        ) : (
                          <span className="slot-device-name" style={{ opacity: 0.4 }}>Idle</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* Connected File Peers */}
              <section className="canvas-card">
                <div className="card-title-simple">
                  <span>Connected File Peers ({nodes.length})</span>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button className="btn btn-sm btn-outline" onClick={() => nodes.forEach((n) => handleEnqueue(n.id, 2))}>
                      + Send 2 Chunks to All
                    </button>
                    {nodes.some(n => n.state === 'DEGRADED_RETRY' || n.state === 'DEGRADED') && (
                      <button className="btn btn-sm btn-outline" onClick={handleClearFaults}>
                        ✓ Recover All
                      </button>
                    )}
                  </div>
                </div>

                <div className="nodes-grid">
                  {nodes.map((node) => {
                    const meta = STATE_META[node.state] || STATE_META.UNINITIALIZED;
                    const slotIndex = activeBatch.indexOf(node.id);
                    const isDegraded = node.state === 'DEGRADED_RETRY' || node.state === 'DEGRADED';

                    return (
                      <div
                        key={node.id}
                        className={`node-card ${slotIndex !== -1 ? 'node-card-active' : ''}`}
                        style={{ borderLeftColor: isDegraded ? 'var(--state-degraded)' : undefined }}
                      >
                        <div className="node-card-header">
                          <strong className="node-name">{node.name}</strong>
                          <span className={`node-badge ${meta.badgeClass}`}>{meta.label}</span>
                        </div>

                        {slotIndex !== -1 && (
                          <div className="slot-indicator">Slot #{slotIndex + 1}</div>
                        )}

                        <div className="node-quick-stats">
                          <span>{node.rssi} dBm</span>
                          <span>·</span>
                          <span>{node.rtt} ms</span>
                          <span>·</span>
                          <span>{ackedChunksMap[node.id] || 0} ACK</span>
                        </div>

                        <div className="buffer-meter">
                          <div className="buffer-label">
                            <span>Buffer Queue</span>
                            <span>{node.queueDepth || 0} chunks</span>
                          </div>
                          <div className="meter-track">
                            <div
                              className="meter-fill"
                              style={{ width: `${Math.min(100, ((node.queueDepth || 0) / 10) * 100)}%` }}
                            />
                          </div>
                        </div>

                        <div className="node-actions-row">
                          <button
                            className="btn btn-sm btn-outline"
                            onClick={() => handleEnqueue(node.id, 3)}
                            title="Queue file chunks to this peer"
                          >
                            +3 Chunks
                          </button>
                          <button
                            className="btn btn-sm btn-outline"
                            onClick={() => handleFaultInjection(node.id, isDegraded ? 'restore' : 'degrade')}
                            title={isDegraded ? 'Recover node link' : 'Simulate signal loss / timeout'}
                          >
                            {isDegraded ? '✓ Recover' : '⚡ Degrade'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* TDM Slot Duration Controls */}
              <section className="canvas-card">
                <div className="tslice-compact">
                  <span className="tslice-compact-label">Slot Duration (T_slice):</span>
                  <div className="tslice-preset-chips">
                    {[100, 250, 500, 1000].map((preset) => (
                      <button
                        key={preset}
                        className={`tslice-chip ${tSliceMs === preset ? 'active' : ''}`}
                        onClick={() => handleTSliceChange(preset)}
                      >
                        {preset}ms
                      </button>
                    ))}
                  </div>
                  <input
                    type="range"
                    min="100"
                    max="1500"
                    step="50"
                    value={tSliceMs}
                    onChange={(e) => handleTSliceChange(Number(e.target.value))}
                    className="slider-input"
                    style={{ flex: 1, maxWidth: '200px' }}
                  />
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                    {tSliceMs} ms
                  </span>
                </div>
              </section>
            </>
          )}

          {/* TAB 2: BLE DEVICE SCANNER */}
          {activeTab === 'BLUETOOTH' && (
            <div className="benchmark-container">
              {/* File Sharing Connection Guide */}
              <div className="guide-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '1.4rem' }}>📡</span>
                  <div>
                    <h3 style={{ fontSize: '0.98rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                      Connect Physical Devices for BLE File Transfer
                    </h3>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
                      Scan nearby Bluetooth devices using your PC radio (Bleak/WinRT) and pair them as file sharing peers
                    </p>
                  </div>
                </div>

                <div className="guide-steps-grid">
                  <div className="guide-step-box">
                    <span className="guide-step-num">Step 1 &bull; Scan</span>
                    <span className="guide-step-title">📡 Discover Nearby Devices</span>
                    <div className="guide-step-desc">
                      Click <strong>Scan Bluetooth Devices</strong>. The scanner uses your host Bluetooth radio via Bleak to discover real peripherals in range.
                    </div>
                  </div>

                  <div className="guide-step-box">
                    <span className="guide-step-num">Step 2 &bull; Pair</span>
                    <span className="guide-step-title">🔗 Add to File Peers</span>
                    <div className="guide-step-desc">
                      Click <strong>+ Add as Peer</strong> on any discovered device (smartphone, earbuds, laptop, ESP32) to add it to the multiplexed file transfer queue.
                    </div>
                  </div>

                  <div className="guide-step-box">
                    <span className="guide-step-num">Step 3 &bull; Send</span>
                    <span className="guide-step-title">📂 Transfer Files</span>
                    <div className="guide-step-desc">
                      Switch to the <strong>File Transfer</strong> tab, choose any document or image, and start multiplexing file chunks across all peers!
                    </div>
                  </div>
                </div>
              </div>

              {/* Scanner Control & Devices */}
              <section className="benchmark-card">
                <div className="card-title">
                  <span>Bluetooth Device Scanner</span>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-primary"
                      onClick={() => {
                        if (transportMode !== 'physical') handleModeSwitch('physical');
                        else handleScanPhysical();
                      }}
                      disabled={isPhysicalScanning}
                    >
                      {isPhysicalScanning ? '🔍 Scanning Radio Spectrum...' : '📡 Scan Bluetooth Devices'}
                    </button>
                    {physicalDiscovered.length > 0 && (
                      <button
                        className="btn btn-secondary"
                        onClick={handleQuickAddAll}
                      >
                        ⚡ Add Top {Math.min(12, physicalDiscovered.length)} as Peers
                      </button>
                    )}
                  </div>
                </div>

                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                  Discover nearby BLE devices and add them as file transfer peers. Each device becomes a logical stream sharing the 4 hardware GATT slots.
                </p>

                {/* Toolbar: Search input + Named Device Toggle Pills */}
                <div className="scanner-toolbar">
                  <input
                    type="text"
                    className="scanner-search-input"
                    placeholder="🔍 Filter devices by name or MAC address (e.g. Buds, Nord, Laptop)..."
                    value={deviceFilter}
                    onChange={(e) => setDeviceFilter(e.target.value)}
                  />
                  <div className="scanner-filter-toggles">
                    <button
                      type="button"
                      className={`filter-pill-btn ${hideUnnamed ? 'active' : ''}`}
                      onClick={() => setHideUnnamed(true)}
                    >
                      ⭐ Named Only ({namedCount})
                    </button>
                    <button
                      type="button"
                      className={`filter-pill-btn ${!hideUnnamed ? 'active' : ''}`}
                      onClick={() => setHideUnnamed(false)}
                    >
                      📡 All ({physicalDiscovered.length})
                    </button>
                  </div>
                </div>

                {/* Filter notification banner */}
                {hideUnnamed && physicalDiscovered.length > namedCount && (
                  <div className="filter-info-banner">
                    <span>
                      🛡️ Showing <strong>{filteredDiscovered.length} named devices</strong>. Filtered out {physicalDiscovered.length - namedCount} unnamed beacons and privacy MACs.
                    </span>
                    <button
                      type="button"
                      className="filter-info-btn"
                      onClick={() => setHideUnnamed(false)}
                    >
                      Show all {physicalDiscovered.length} devices
                    </button>
                  </div>
                )}

                {/* Manual MAC address pairing input */}
                <form onSubmit={handleManualPair} style={{ display: 'flex', gap: '8px', margin: '12px 0 16px 0' }}>
                  <input
                    type="text"
                    className="config-input"
                    style={{ flex: 1 }}
                    placeholder="Enter MAC address (e.g. AA:BB:CC:11:22:33)..."
                    value={manualMac}
                    onChange={(e) => setManualMac(e.target.value)}
                  />
                  <input
                    type="text"
                    className="config-input"
                    style={{ width: '180px' }}
                    placeholder="Device Name (optional)"
                    value={manualName}
                    onChange={(e) => setManualName(e.target.value)}
                  />
                  <button type="submit" className="btn btn-secondary">
                    + Add MAC
                  </button>
                </form>

                {/* Discovered Real Bluetooth Peripherals Grid */}
                <div>
                  {isPhysicalScanning ? (
                    <div style={{ background: 'var(--bg-surface)', padding: '36px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: '2rem', marginBottom: '8px', animation: 'spin 1.5s linear infinite' }}>📡</div>
                      <h4 style={{ color: 'var(--accent-cyan)', margin: '0 0 6px 0' }}>Scanning Bluetooth Spectrum...</h4>
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                        Bleak WinRT adapter is actively discovering advertising devices in radio range (3s)...
                      </p>
                    </div>
                  ) : filteredDiscovered.length === 0 ? (
                    <div style={{ background: 'var(--bg-surface)', padding: '28px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
                      <p style={{ color: 'var(--text-muted)', marginBottom: '12px' }}>
                        {physicalDiscovered.length === 0
                          ? 'No devices scanned yet. Click "Scan Bluetooth Devices" to discover nearby BLE hardware.'
                          : 'No devices match your search filter.'}
                      </p>
                      <button className="btn btn-primary" onClick={handleScanPhysical} disabled={isPhysicalScanning}>
                        Start Real Bluetooth Scan Now
                      </button>
                    </div>
                  ) : (
                    <div className="physical-devices-grid">
                      {filteredDiscovered.map((dev) => {
                        const isAlreadyPaired = activeNodeIds.has(dev.device_id);
                        const testResult = testResultMap[dev.device_id];
                        const isTesting = testingDevice === dev.device_id;
                        const quality = getRssiQuality(dev.rssi);

                        return (
                          <div key={dev.device_id} className="physical-device-card">
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                                <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                                  {dev.name || 'BLE Device'}
                                </strong>
                                <span className="node-badge badge-physical">BLE</span>
                              </div>
                              <div style={{ marginBottom: '8px' }}>
                                <span className="mac-pill">{dev.device_id}</span>
                              </div>

                              {/* RSSI Signal Bar */}
                              <div className="rssi-indicator">
                                <span style={{ color: quality.color, fontWeight: 600 }}>
                                  📶 {dev.rssi} dBm
                                </span>
                                <div className="rssi-bar-outer">
                                  <div
                                    className="rssi-bar-inner"
                                    style={{ width: `${quality.percent}%`, background: quality.color }}
                                  />
                                </div>
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                                  ({quality.label})
                                </span>
                              </div>

                              {/* Test Link Result feedback */}
                              {testResult && (
                                <div style={{
                                  marginTop: '8px',
                                  padding: '5px 8px',
                                  borderRadius: '4px',
                                  fontSize: '0.72rem',
                                  lineHeight: '1.3',
                                  background: testResult.success ? 'rgba(93, 202, 165, 0.12)' : 'rgba(240, 153, 123, 0.12)',
                                  border: `1px solid ${testResult.success ? 'var(--state-active)' : 'var(--state-degraded)'}`,
                                  color: testResult.success ? 'var(--state-active)' : 'var(--text-primary)',
                                }}>
                                  {testResult.success
                                    ? `✓ Connected (${testResult.services_count} GATT Services)`
                                    : `ℹ ${testResult.message || 'Connection test finished'}`}
                                </div>
                              )}
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '12px' }}>
                              <div style={{ display: 'flex', gap: '6px' }}>
                                <button
                                  className="btn btn-outline"
                                  style={{ flex: 1, fontSize: '0.72rem', padding: '6px' }}
                                  onClick={() => handleTestConnect(dev)}
                                  disabled={isTesting}
                                  title="Test physical GATT service connectivity"
                                >
                                  {isTesting ? '⚡ Probing...' : '⚡ Test Link'}
                                </button>
                                {isAlreadyPaired ? (
                                  <button
                                    className="btn btn-secondary"
                                    style={{ flex: 2, fontSize: '0.72rem', padding: '6px' }}
                                    onClick={() => handleUnpairNode(dev.device_id)}
                                  >
                                    ✓ Added (Remove)
                                  </button>
                                ) : (
                                  <button
                                    className="btn btn-primary"
                                    style={{ flex: 2, fontSize: '0.72rem', padding: '6px' }}
                                    onClick={() => handlePairPhysical(dev)}
                                  >
                                    ➕ Add as Peer
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </section>
            </div>
          )}
        </div>
      </main>

      {/* Off-Canvas Slide-Over Debug Event Stream Console */}
      {showDebugStream && (
        <div className="debug-drawer-overlay" onClick={() => setShowDebugStream(false)}>
          <aside className="debug-drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="feed-card debug-drawer-card">
              <div className="card-title">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>🛠️ Live Event Stream</span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)' }}>
                    {filteredEvents.length} events
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    className="btn btn-outline"
                    style={{ fontSize: '0.68rem', padding: '2px 8px' }}
                    onClick={clearEvents}
                    title="Clear event feed history"
                  >
                    🗑️ Clear
                  </button>
                  <button
                    className="btn btn-outline"
                    style={{ fontSize: '0.75rem', padding: '2px 8px' }}
                    onClick={() => setShowDebugStream(false)}
                    title="Close debug console"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Feed Filter Chips */}
              <div className="feed-filter-chips">
                {['ALL', 'ROTATIONS', 'BUFFERS', 'CHUNKS'].map((filterKey) => (
                  <button
                    key={filterKey}
                    className={`feed-filter-chip ${feedFilter === filterKey ? 'active' : ''}`}
                    onClick={() => setFeedFilter(filterKey)}
                  >
                    {filterKey}
                  </button>
                ))}
              </div>

              <div className="feed-list">
                {filteredEvents.length === 0 ? (
                  <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    No events captured yet.
                  </div>
                ) : (
                  filteredEvents.map((ev, i) => (
                    <div key={i} className="feed-item">
                      <div className="feed-item-header">
                        <span className="feed-type">{ev.type}</span>
                        <span className="feed-time">{ev.time}</span>
                      </div>
                      <div className="feed-data">
                        {JSON.stringify(ev.data, null, 2)}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
