"""CSV Export Generator for BT-Mux Benchmark Telemetry Summaries.

Authoritative source: SRS REQ-13.
Computes and formats global Packet Delivery Ratios (PDR), average RTT,
handoff context-switch overhead, and per-node metrics into standard CSV.
"""
import csv
import io
from typing import Any, Dict, List


def generate_telemetry_csv(
    session: Dict[str, Any],
    telemetry: Dict[str, Any],
    nodes: List[Dict[str, Any]],
) -> str:
    """Generate standard RFC 4180 CSV report from session telemetry and node records (REQ-13).
    
    Includes:
    - Session metadata header (test name, slice duration, hardware limit, timestamps).
    - Summary benchmark metrics (Total Sent, Total Received, Global PDR, Mean RTT, Handoff Overhead).
    - Per-node breakdown table (Node ID, State, Average RSSI, Average RTT).
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Section: Session Benchmark Overview (REQ-13)
    writer.writerow(["# BT-Mux Benchmark Telemetry Summary Export (SRS REQ-13)"])
    writer.writerow([])
    writer.writerow(["Session ID", session.get("id") or session.get("_id", "N/A")])
    writer.writerow(["Test Name", session.get("test_name", "N/A")])
    writer.writerow(["Time-Slice Window (T_slice ms)", session.get("slice_duration_ms", 500)])
    writer.writerow(["Host Physical Cap (N_max)", session.get("max_hardware_limit", 4)])
    writer.writerow(["Session Status", session.get("status", "N/A")])
    writer.writerow(["Created At", session.get("created_at", "N/A")])
    writer.writerow(["Started At", session.get("started_at", "N/A")])
    writer.writerow(["Ended At", session.get("ended_at", "N/A")])
    writer.writerow([])

    # 2. Section: Global Performance Aggregates
    total_sent = telemetry.get("total_packets_sent", 0)
    total_received = telemetry.get("total_packets_received", 0)
    pdr = telemetry.get("pdr", 0.0)
    # Recalculate or format PDR percentage
    pdr_pct = f"{pdr * 100:.2f}%"
    avg_rtt = f"{telemetry.get('average_rtt', 0.0):.2f}"
    avg_handoff = f"{telemetry.get('average_handoff_latency', 0.0):.2f}"

    writer.writerow(["=== Global Benchmark Metrics ==="])
    writer.writerow(["Metric", "Value", "Target Reference"])
    writer.writerow(["Total Packets Sent", total_sent, "N/A"])
    writer.writerow(["Total Packets Received", total_received, "N/A"])
    writer.writerow(["Packet Delivery Ratio (PDR)", pdr_pct, ">= 95% at N=10 (SRS 5.1)"])
    writer.writerow(["Average Round-Trip Time (RTT ms)", f"{avg_rtt} ms", "N/A"])
    writer.writerow(["Average Handoff Overhead", f"{avg_handoff} ms", "<= 300 ms (SRS 5.1)"])
    writer.writerow([])

    # 3. Section: Per-Node Metric Breakdown
    writer.writerow(["=== Per-Node Stream Metrics ==="])
    writer.writerow(["Node / Device ID", "Priority Rank", "Socket Status", "Average RSSI (dBm)", "Average RTT (ms)"])

    # Map embedded node metrics from telemetry if available
    telemetry_nodes = {n.get("node_id"): n for n in telemetry.get("nodes", [])}

    if nodes:
        for node in nodes:
            dev_id = node.get("device_id") or node.get("id") or "unknown"
            t_node = telemetry_nodes.get(dev_id, {})
            rssi = t_node.get("average_rssi", "N/A")
            rtt = t_node.get("average_rtt", "N/A")
            writer.writerow([
                dev_id,
                node.get("priority_rank", 0),
                node.get("status", "UNINITIALIZED"),
                f"{rssi}" if rssi != "N/A" else "N/A",
                f"{rtt}" if rtt != "N/A" else "N/A",
            ])
    else:
        # Fall back to telemetry embedded nodes
        for t_node in telemetry.get("nodes", []):
            writer.writerow([
                t_node.get("node_id", "unknown"),
                "N/A",
                "N/A",
                t_node.get("average_rssi", "N/A"),
                t_node.get("average_rtt", "N/A"),
            ])

    return output.getvalue()
