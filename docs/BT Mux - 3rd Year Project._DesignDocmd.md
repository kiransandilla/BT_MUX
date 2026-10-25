**Software Design Document: BT-Mux Middleware Engine (v1.0)**  
**Prepared by:** Technical Lead

**Organization:** Indian Institute of Information Technology (IIIT), Pune

**Date:** September 2026

## **1\. System Overview**

BT-Mux is a user-space virtual socket abstraction middleware designed to bypass the physical hardware limits ($N\_{\\text{max}} \= 4\\text{–}7$) of standard Bluetooth Low Energy (BLE) controllers. By utilizing Time-Division Multiplexing (TDM) and local RAM session caching, the system creates the illusion of $N \\ge 12$ continuous logical data streams, intercepting native GATT\_NO\_RESOURCES hardware overflow errors and dynamically rotating active physical radio slots.

## **2\. System Architecture**

The architecture is decoupled into three functional execution domains, allowing concurrent development across frontend, backend/database, and AI/Python subsystems.

## **3\. Module Specifications**

### **3.1 Virtual Socket Pipeline (Core Middleware)**

* **Purpose:** Interfaces directly with native BLE hardware interfaces to execute the TDM round-robin loop.  
*   
* **Execution Logic:**  
* 

  * Initializes asynchronous connections using configurable time slices ($T\_{\\text{slice}} \= 200\\text{–}500\\text{ ms}$).  
  *   
  * Prior to releasing a physical slot, the engine caches byte-stream sequence markers and unacknowledged payload chunks in local RAM.  
  *   
  * Upon re-establishment of the physical link, data transfer resumes from the exact stored chunk offset, preventing full GAP pairing overhead.  
  * 

### **3.2 RSSI-Guided Heuristic Engine**

* **Purpose:** Replaces static round-robin scheduling with dynamic, predictive time-slot allocation.  
*   
* **Execution Logic:** Built as an isolated Python microservice, this module ingests raw Received Signal Strength Indicator (RSSI) power values alongside node priority ranks. It computes optimal $T\_{\\text{slice}}$ durations in periodic batches, ensuring highly degraded nodes do not stall the core multiplexing loop while maintaining efficient hardware utilization.  
* 

### **3.3 Diagnostic Testbed & IPC Pipeline**

* **Purpose:** Provides an interactive topological canvas to monitor real-time context-switching states and latency metrics without degrading core engine performance.  
*   
* **Execution Logic:** Receives high-velocity JSON state events via WebSockets. To prevent stale closures and UI thread blocking during rapid multiplexer swapping, the interface relies strictly on functional state updates (e.g., setMetrics(prev \=\> prev \+ incoming\_payload)) for real-time metric accumulation rather than direct state mutation.  
* 

## **4\. Database Design (Telemetry Store)**

The persistence layer relies on a normalized document-oriented schema to log time-series benchmarks for analytical graph generation.

* sessions **(Parent Entity):** Records experimental parameters for isolated test runs, including hardware cap limits (N\_max), global T\_slice targets, and total virtual devices.  
*   
* nodes **(Child Entity):** Linked1:N to sessions. Stores metadata for individual peripheral edge devices, including priority tier and hardware type.  
*   
* telemetry\_logs **(Time-Series Entity):** Mapped dynamically to session\_id and node\_id. Stores high-frequency captures of round-trip delays, context-switch handoff latency, and packet delivery ratios (PDR).  
* 

## **5\. Technical Constraints**

* **Handoff Latency:** Physical link swapping must fully execute within 300ms to maintain seamless logical abstraction.  
* **Hardware Caps:** The host system's physical connection limits must be automatically polled and respected to avoid driver-level kernel panics.  
* **Scalability:** Initial proof-of-concept deployment must successfully maintain 10-12 active logical streams, with protocol design allowing unrestricted upper limits in mature deployments.