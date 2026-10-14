/*
  BT-Mux ESP32 Nordic UART Service (NUS) Peripheral Firmware
  
  Description:
  Acts as a real BLE peripheral for testing the BT-Mux user-space
  virtual socket multiplexing system. Receives file chunks from BT-Mux
  over GATT write, reassembles incoming byte streams, and sends ACKs
  via GATT notifications.

  Hardware Target: ESP32 / ESP32-WROOM-32 / ESP32-C3 / ESP32-S3
  Dependencies: ESP32 BLE Arduino library (built into ESP32 board package)
*/

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Standard Nordic UART Service (NUS) UUIDs matching BT-Mux BLETransport HAL
#define NUS_SERVICE_UUID           "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_RX     "6E400002-B5A3-F393-E0A9-E50E24DCCA9E" // Central -> Peripheral (Write)
#define CHARACTERISTIC_UUID_TX     "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" // Peripheral -> Central (Notify)

BLEServer* pServer = NULL;
BLECharacteristic* pTxCharacteristic = NULL;
BLECharacteristic* pRxCharacteristic = NULL;

bool deviceConnected = false;
bool oldDeviceConnected = false;
uint32_t totalBytesReceived = 0;
uint32_t totalChunksReceived = 0;

// Server connection callbacks
class ServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        totalBytesReceived = 0;
        totalChunksReceived = 0;
        Serial.println("\n[+] Central connected (BT-Mux host)!");
    };

    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        Serial.println("\n[-] Central disconnected.");
        Serial.printf("[*] Session Summary: %u chunks, %u bytes received.\n", totalChunksReceived, totalBytesReceived);
    }
};

// RX Characteristic callback (Receives file chunks from BT-Mux)
class RxCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        String rxValue = pCharacteristic->getValue();
        size_t len = rxValue.length();

        if (len > 0) {
            totalChunksReceived++;
            totalBytesReceived += len;

            Serial.printf("[RX Chunk #%u] %u bytes | Total: %u bytes\n", totalChunksReceived, len, totalBytesReceived);

            // Optional: Print ASCII preview of received chunk
            if (len <= 64) {
                Serial.print("   Preview: ");
                for (size_t i = 0; i < len; i++) {
                    char c = rxValue[i];
                    if (c >= 32 && c <= 126) Serial.print(c);
                    else Serial.print('.');
                }
                Serial.println();
            }

            // Send ACK notification back to BT-Mux host
            if (deviceConnected && pTxCharacteristic != NULL) {
                char ackMsg[32];
                snprintf(ackMsg, sizeof(ackMsg), "ACK:%u", totalChunksReceived);
                pTxCharacteristic->setValue((uint8_t*)ackMsg, strlen(ackMsg));
                pTxCharacteristic->notify();
            }
        }
    }
};

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("=================================================");
    Serial.println("  BT-Mux ESP32 BLE Peripheral (Nordic UART NUS)");
    Serial.println("=================================================");

    // Initialize BLE Device
    BLEDevice::init("BTMUX_ESP32_01");

    // Create BLE Server
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());

    // Create NUS Service
    BLEService *pService = pServer->createService(NUS_SERVICE_UUID);

    // Create RX Characteristic (Central writes chunks here)
    pRxCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID_RX,
        BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR
    );
    pRxCharacteristic->setCallbacks(new RxCallbacks());

    // Create TX Characteristic (Peripheral notifies ACKs to Central)
    pTxCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID_TX,
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pTxCharacteristic->addDescriptor(new BLE2902());

    // Start NUS Service
    pService->start();

    // Configure Advertising
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(NUS_SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);  // helper for iPhone connections
    pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();

    Serial.printf("[+] BLE MAC Address: %s\n", BLEDevice::getAddress().toString().c_str());
    Serial.println("[+] Advertising as 'BTMUX_ESP32_01' with NUS Service.");
    Serial.println("[*] Waiting for incoming BT-Mux connections...\n");
}

void loop() {
    // Restart advertising upon disconnect
    if (!deviceConnected && oldDeviceConnected) {
        delay(500); // give the bluetooth stack the chance to get things ready
        pServer->startAdvertising();
        Serial.println("[+] Restarted BLE advertising...");
        oldDeviceConnected = deviceConnected;
    }
    // Update state on connect
    if (deviceConnected && !oldDeviceConnected) {
        oldDeviceConnected = deviceConnected;
    }
    delay(50);
}
