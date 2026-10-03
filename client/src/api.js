/**
 * BT-Mux API Client
 * Centralized fetch functions for sessions, devices, nodes, and telemetry.
 */
const BASE_URL = 'http://localhost:8000/api';

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}

export async function fetchSessions() {
  const res = await fetch(`${BASE_URL}/sessions`);
  return res.json();
}

export async function createSession(payload) {
  const res = await fetch(`${BASE_URL}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function updateSessionStatus(sessionId, status) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return res.json();
}

export async function fetchDevices() {
  const res = await fetch(`${BASE_URL}/devices`);
  return res.json();
}

export async function registerDevice(payload) {
  const res = await fetch(`${BASE_URL}/devices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function fetchSessionNodes(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/nodes`);
  return res.json();
}

export async function addSessionNode(sessionId, payload) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function fetchTelemetry(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/telemetry`);
  if (!res.ok) return null;
  return res.json();
}
