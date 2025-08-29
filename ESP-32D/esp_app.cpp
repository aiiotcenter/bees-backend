// ESP32 Beehive Monitor with Web Server and Offline Storage - version 19

/*
Notice: 
The "WiFi Configuration", "Web Server Configuration" and "Static IP Configuration" 
need to be specified!
*/ 

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <DHT.h>
#include <time.h>
#include <SPIFFS.h>
#include <WebServer.h>
#include <ESPmDNS.h>

// DHT11 Configuration
#define DHT_PIN 4        // GPIO4 for DHT11 data pin
#define DHT_TYPE DHT11   // DHT11 sensor type
DHT dht(DHT_PIN, DHT_TYPE);

// WiFi Configuration
const char* ssid = "WIFI_SSID";
const char* password = "WIFI_PASSWORD";

// Static IP Configuration
IPAddress staticIP(192, 168, 254, 187);     // Static IP address
IPAddress gateway(192, 168, 254, 1);        // Gateway (usually router IP)
IPAddress subnet(255, 255, 255, 0);         // Subnet mask
IPAddress primaryDNS(8, 8, 8, 8);           // Primary DNS (Google)
IPAddress secondaryDNS(8, 8, 4, 4);         // Secondary DNS (Google)

// API Configuration
const char* apiUrl = "http://100.70.97.126:9602/api/records";
const char* statusUrl = "http://100.70.97.126:9602/api/hives/status/1";
const char* locationUrl = "http://100.70.97.126:9602/api/hives/check-location/1";

// Web Server Configuration
WebServer server(80);
String webUsername = "username";
String webPassword = "password";

// Timing Configuration
const unsigned long READING_INTERVAL = 180000;  // 3 minutes in milliseconds
const int MAX_READINGS = 3;                     // Number of readings per cycle
const unsigned long WIFI_TIMEOUT = 10000;      // WiFi connection timeout
const unsigned long HTTP_TIMEOUT = 15000;      // HTTP request timeout
const int MAX_RETRY_ATTEMPTS = 3;              // Maximum retry attempts

// Global Variables
Preferences preferences;
unsigned long lastReadingTime = 0;
int readingCount = 0;
bool wifiConnected = false;
bool webServerStarted = false;  // Adding this flag to track web server status
String offlineData = "";
int offlineRecordCount = 0;

// Structure for sensor reading
struct SensorReading {
  String hiveId;
  float temperature;
  float humidity;
  int weight;
  int distance;
  int soundStatus;
  int isDoorOpen;
  int numOfIn;
  int numOfOut;
  float latitude;
  float longitude;
  bool status;
  String recordedAt;
};

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("ESP32 Beehive Monitor Starting...");
  
  // Initialize SPIFFS for file storage
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS initialization failed!");
  } else {
    Serial.println("SPIFFS initialized");
  }
  
  // Initialize preferences for persistent storage
  preferences.begin("beehive", false);
  
  // Load offline record count from preferences
  offlineRecordCount = preferences.getInt("offlineCount", 0);
  Serial.println("Found " + String(offlineRecordCount) + " offline records");
  
  // Initialize DHT sensor
  dht.begin();
  Serial.println("DHT11 sensor initialized");
  
  // Setup time
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  
  // Initialize WiFi
  setupWiFi();
  
  // Setup web server if WiFi connected
  if (wifiConnected) {
    setupWebServer();
    webServerStarted = true;
  }
  
  // Send initial status
  if (wifiConnected) {
    sendStatusUpdate(1, true);
  }
  
  Serial.println("Beehive monitor ready!");
  Serial.println("=====================================");
}

void loop() {
  // Handle web server requests
  if (wifiConnected && webServerStarted) {
    server.handleClient();
  }
  
  // Check for serial commands
  checkSerialCommands();
  
  // Check WiFi connection
  checkWiFiConnection();
  
  // Try to send pending offline data if connected (but limit attempts)
  static unsigned long lastOfflineAttempt = 0;
  static int consecutiveFailures = 0;
  
  if (wifiConnected && offlineRecordCount > 0 && millis() - lastOfflineAttempt > 30000) { // Try every 30 seconds
    Serial.println("Attempting to send " + String(offlineRecordCount) + " offline records...");
    
    int previousCount = offlineRecordCount;
    sendOfflineData();
    lastOfflineAttempt = millis();
    
    // Check if we made progress
    if (offlineRecordCount >= previousCount) {
      consecutiveFailures++;
      Serial.println("No progress sending offline data (attempt " + String(consecutiveFailures) + "/5)");
      
    // If we fail 5 times in a row, clear corrupted data
    //   if (consecutiveFailures >= 5) {
    //     Serial.println("Clearing potentially corrupted offline data...");
    //     clearAllOfflineData();
    //     consecutiveFailures = 0;
    //   }
    } else {
      consecutiveFailures = 0; // Reset on success
    }
  }
  
  // Collect sensor readings
  if (millis() - lastReadingTime >= READING_INTERVAL || lastReadingTime == 0) {
    Serial.println("\nCollecting sensor reading #" + String(readingCount + 1) + "/" + String(MAX_READINGS));
    
    SensorReading reading = collectSensorReading();
    
    if (reading.status) {
      // Show timestamp of each reading
      Serial.println("Recorded at: " + reading.recordedAt);
      
      // Try to send immediately if WiFi is connected
      if (wifiConnected) {
        if (sendSensorData(reading)) {
          Serial.println("Data sent successfully");
        } else {
          Serial.println("Failed to send, saving offline");
          saveOfflineReading(reading);
        }
      } else {
        Serial.println("No WiFi, saving offline");
        saveOfflineReading(reading);
      }
    } else {
      Serial.println("Invalid sensor reading, skipping");
    }
    
    readingCount++;
    lastReadingTime = millis();
    
    // Reset reading count after MAX_READINGS
    if (readingCount >= MAX_READINGS) {
      readingCount = 0;
      Serial.println("Completed reading cycle");
      Serial.println("Current offline records: " + String(offlineRecordCount));
      Serial.println("=====================================");
    }
  }
  
  // Small delay to prevent watchdog issues
  delay(1000);
}

void setupWebServer() {
  // Start mDNS service
  if (MDNS.begin("esp32-beehive")) {
    Serial.println("mDNS responder started: http://esp32-beehive.local");
  }
  
  // Define web server routes
  server.on("/", handleRoot);
  server.on("/api/status", handleApiStatus);
  server.on("/api/data", handleApiData);
  server.on("/api/offline", handleApiOffline);
  server.on("/api/clear", HTTP_POST, handleApiClear);
  server.on("/api/send", HTTP_POST, handleApiSend);
  server.on("/api/reboot", HTTP_POST, handleApiReboot);
  server.onNotFound(handleNotFound);
  
  // Enable CORS for API access
  server.enableCORS(true);
  
  server.begin();
  webServerStarted = true;
  Serial.println("Web server started on port 80");
  Serial.println("Access via: http://" + WiFi.localIP().toString());
}

void checkSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toLowerCase();
    
    if (command == "status") {
      printSystemInfo();
    } else if (command == "clear") {
      clearAllOfflineData();
    } else if (command == "wifi") {
      Serial.println("WiFi Status: " + String(wifiConnected ? "Connected" : "Disconnected"));
      if (wifiConnected) {
        Serial.println("SSID: " + WiFi.SSID());
        Serial.println("IP Address: " + WiFi.localIP().toString());
        Serial.println("Gateway: " + WiFi.gatewayIP().toString());
        Serial.println("Subnet Mask: " + WiFi.subnetMask().toString());
        Serial.println("DNS 1: " + WiFi.dnsIP(0).toString());
        Serial.println("DNS 2: " + WiFi.dnsIP(1).toString());
        Serial.println("Signal Strength: " + String(WiFi.RSSI()) + " dBm");
        Serial.println("MAC Address: " + WiFi.macAddress());
      }
    } else if (command == "offline") {
      Serial.println("Offline records: " + String(offlineRecordCount));
      Serial.println("Actual count: " + String(countActualOfflineRecords()));
    } else if (command == "send") {
      if (wifiConnected) {
        Serial.println("Manually triggering offline data send...");
        sendOfflineData();
      } else {
        Serial.println("No WiFi connection");
      }
    } else if (command == "help") {
      Serial.println("Available commands:");
      Serial.println("  status  - Show system information");
      Serial.println("  wifi    - Show WiFi status");
      Serial.println("  offline - Show offline record count");
      Serial.println("  send    - Manually send offline data");
      Serial.println("  clear   - Clear all offline data");
      Serial.println("  help    - Show this help");
    } else if (command.length() > 0) {
      Serial.println("Unknown command: " + command);
      Serial.println("Type 'help' for available commands");
    }
  }
}

void setupWiFi() {
  Serial.print("Connecting to WiFi: " + String(ssid));
  Serial.println(" (Static IP: " + staticIP.toString() + ")");
  
  // Configure static IP before connecting
  if (!WiFi.config(staticIP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println("Static IP configuration failed!");
  }
  
  WiFi.begin(ssid, password);
  
  unsigned long startAttempt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < WIFI_TIMEOUT) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println();
    Serial.println("WiFi connected with static IP!");
    Serial.println("IP address: " + WiFi.localIP().toString());
    Serial.println("Gateway: " + WiFi.gatewayIP().toString());
    Serial.println("Subnet mask: " + WiFi.subnetMask().toString());
    Serial.println("DNS 1: " + WiFi.dnsIP(0).toString());
    Serial.println("DNS 2: " + WiFi.dnsIP(1).toString());
    Serial.println("Signal strength: " + String(WiFi.RSSI()) + " dBm");
  } else {
    wifiConnected = false;
    Serial.println();
    Serial.println("WiFi connection failed!");
    Serial.println("Will operate in offline mode");
  }
}

void checkWiFiConnection() {
  bool previousState = wifiConnected;
  wifiConnected = (WiFi.status() == WL_CONNECTED);
  
  if (!wifiConnected && previousState) {
    Serial.println("WiFi connection lost");
    webServerStarted = false;  // Mark web server as stopped
  } else if (wifiConnected && !previousState) {
    Serial.println("WiFi connection restored");
    Serial.println("IP address: " + WiFi.localIP().toString());
    // Setup web server if it wasn't running
    if (!webServerStarted) {
      setupWebServer();
    }
  }
  
  // Try to reconnect if disconnected
  if (!wifiConnected) {
    static unsigned long lastReconnectAttempt = 0;
    if (millis() - lastReconnectAttempt > 30000) { // Try every 30 seconds
      Serial.println("Attempting WiFi reconnection with static IP...");
      WiFi.disconnect();
      
      // Reconfigure static IP for reconnection
      if (!WiFi.config(staticIP, gateway, subnet, primaryDNS, secondaryDNS)) {
        Serial.println("Static IP reconfiguration failed!");
      }
      
      WiFi.begin(ssid, password);
      lastReconnectAttempt = millis();
    }
  }
}

SensorReading collectSensorReading() {
  SensorReading reading;
  
  // Read DHT11 sensor
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  
  // Check if readings are valid
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("DHT11 reading failed!");
    reading.status = false;
    reading.temperature = 0;
    reading.humidity = 0;
  } else {
    reading.status = true;
    reading.temperature = temperature;
    reading.humidity = humidity;
    Serial.println("Temperature: " + String(temperature) + "°C");
    Serial.println("Humidity: " + String(humidity) + "%");
  }
  
  // Set sensor values (not available on ESP32 yet)
  reading.hiveId = "1";
  reading.weight = 0;
  reading.distance = 0;
  reading.soundStatus = 0;
  reading.isDoorOpen = 0;
  reading.numOfIn = 0;
  reading.numOfOut = 0;
  reading.latitude = 0.0;
  reading.longitude = 0.0;
  reading.recordedAt = getCurrentTimestamp();
  
  return reading;
}

String getCurrentTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    // If NTP time is not available, use millis() as fallback
    return "offline_" + String(millis());
  }
  
  char timestamp[30];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S.000Z", &timeinfo);
  return String(timestamp);
}

bool sendSensorData(SensorReading reading) {
  if (!wifiConnected) return false;
  
  HTTPClient http;
  http.begin(apiUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(HTTP_TIMEOUT);
  
  // Create JSON payload
  DynamicJsonDocument doc(1024);
  doc["hiveId"] = reading.hiveId;
  doc["temperature"] = String(reading.temperature);
  doc["humidity"] = String(reading.humidity);
  doc["weight"] = reading.weight;
  doc["distance"] = reading.distance;
  doc["soundStatus"] = reading.soundStatus;
  doc["isDoorOpen"] = reading.isDoorOpen;
  doc["numOfIn"] = reading.numOfIn;
  doc["numOfOut"] = reading.numOfOut;
  doc["latitude"] = String(reading.latitude);
  doc["longitude"] = String(reading.longitude);
  doc["status"] = reading.status;
  doc["recordedAt"] = reading.recordedAt;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int httpResponseCode = http.POST(jsonString);
  
  if (httpResponseCode == 200) {
    String response = http.getString();
    Serial.println("API Response: " + String(httpResponseCode) + " - " + response);
    http.end();
    return true;
  } else {
    Serial.println("HTTP Error: " + String(httpResponseCode));
    if (httpResponseCode > 0) {
      Serial.println("Response: " + http.getString());
    }
    http.end();
    return false;
  }
}

bool sendStatusUpdate(int hiveId, bool status) {
  if (!wifiConnected) {
    Serial.println("No WiFi - status update will be sent when connected");
    return false;
  }
  
  HTTPClient http;
  http.begin(statusUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(HTTP_TIMEOUT);
  
  DynamicJsonDocument doc(256);
  doc["status"] = status;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int httpResponseCode = http.PUT(jsonString);
  
  if (httpResponseCode == 200) {
    String response = http.getString();
    Serial.println("Status API Response: " + String(httpResponseCode) + " - " + response);
    http.end();
    return true;
  } else {
    Serial.println("Status Update Error: " + String(httpResponseCode));
    http.end();
    return false;
  }
}

void saveOfflineReading(SensorReading reading) {
  // Create JSON for offline storage
  DynamicJsonDocument doc(1024);
  doc["hiveId"] = reading.hiveId;
  doc["temperature"] = String(reading.temperature);
  doc["humidity"] = String(reading.humidity);
  doc["weight"] = reading.weight;
  doc["distance"] = reading.distance;
  doc["soundStatus"] = reading.soundStatus;
  doc["isDoorOpen"] = reading.isDoorOpen;
  doc["numOfIn"] = reading.numOfIn;
  doc["numOfOut"] = reading.numOfOut;
  doc["latitude"] = String(reading.latitude);
  doc["longitude"] = String(reading.longitude);
  doc["status"] = reading.status;
  doc["recordedAt"] = reading.recordedAt;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Try to save to SPIFFS file first
  String filename = "/offline_" + String(millis()) + ".json"; // Use millis for unique filename
  File file = SPIFFS.open(filename, FILE_WRITE);
  
  if (file) {
    file.println(jsonString);
    file.close();
    offlineRecordCount++;
    preferences.putInt("offlineCount", offlineRecordCount);
    Serial.println("Saved offline record to SPIFFS: " + filename);
    Serial.println("Total offline records: " + String(offlineRecordCount));
  } else {
    Serial.println("SPIFFS save failed, trying preferences...");
    
    // Fallback: try to save in preferences (limited space)
    bool saved = false;
    for (int i = 0; i < 10; i++) {
      String key = "offline" + String(i);
      String existingData = preferences.getString(key.c_str(), "");
      if (existingData.length() == 0) {
        if (preferences.putString(key.c_str(), jsonString)) {
          offlineRecordCount++;
          preferences.putInt("offlineCount", offlineRecordCount);
          Serial.println("Saved offline record in preferences: " + key);
          Serial.println("Total offline records: " + String(offlineRecordCount));
          saved = true;
          break;
        }
      }
    }
    
    if (!saved) {
      Serial.println("Failed to save offline record - storage full");
    }
  }
}

void sendOfflineData() {
  int totalSent = 0;
  int maxAttempts = 10; // Limit attempts to prevent infinite loop
  int attemptCount = 0;
  
  Serial.println("Starting offline data transmission...");
  
  // First try to send files from SPIFFS
  File root = SPIFFS.open("/");
  if (!root) {
    Serial.println("Failed to open SPIFFS root directory");
    return;
  }
  
  File file = root.openNextFile();
  
  while (file && attemptCount < maxAttempts) {
    String filename = file.name();
    if (filename.startsWith("/offline_") && filename.endsWith(".json")) {
      attemptCount++;
      Serial.println("Attempting to send: " + filename);
      
      String content = file.readString();
      file.close();
      
      // Validate JSON content before sending
      if (content.length() > 10 && content.indexOf("{") >= 0) {
        if (sendOfflineRecord(content)) {
          if (SPIFFS.remove(filename)) {
            totalSent++;
            Serial.println("Sent and deleted: " + filename);
          } else {
            Serial.println("Sent but failed to delete: " + filename);
          }
        } else {
          Serial.println("Failed to send: " + filename);
          break; // Stop trying if one fails
        }
      } else {
        Serial.println("Removing corrupted file: " + filename);
        SPIFFS.remove(filename);
      }
      
      delay(2000); // Longer delay between requests
    }
    file = root.openNextFile();
  }
  root.close();
  
  // Then try to send from preferences as fallback
  for (int i = 0; i < 10 && attemptCount < maxAttempts; i++) {
    String key = "offline" + String(i);
    String data = preferences.getString(key.c_str(), "");
    
    if (data.length() > 10) { // Basic validation
      attemptCount++;
      Serial.println("Sending from preferences: " + key);
      
      if (sendOfflineRecord(data)) {
        preferences.remove(key.c_str());
        totalSent++;
        Serial.println("Sent offline record from preferences: " + key);
      } else {
        Serial.println("Failed to send from preferences: " + key);
        break; // Stop if sending fails
      }
      
      delay(2000); // Delay between requests
    }
  }
  
  if (totalSent > 0) {
    // Recalculate offline count by checking what's actually left
    offlineRecordCount = countActualOfflineRecords();
    preferences.putInt("offlineCount", offlineRecordCount);
    Serial.println("Successfully sent " + String(totalSent) + " offline records");
    Serial.println("Remaining offline records: " + String(offlineRecordCount));
  } else {
    Serial.println("No records were sent successfully");
  }
}

bool sendOfflineRecord(String jsonData) {
  if (!wifiConnected) return false;
  
  HTTPClient http;
  http.begin(apiUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(HTTP_TIMEOUT);
  
  Serial.println("Sending: " + jsonData.substring(0, 100) + "..."); // Show first 100 chars
  
  int httpResponseCode = http.POST(jsonData);
  
  if (httpResponseCode == 200) {
    String response = http.getString();
    Serial.println("Offline record sent successfully: " + String(httpResponseCode));
    http.end();
    return true;
  } else {
    Serial.println("Failed to send offline record: " + String(httpResponseCode));
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Response: " + response.substring(0, 200)); // Limit response length
    }
    http.end();
    return false;
  }
}

int countActualOfflineRecords() {
  int count = 0;
  
  // Count files in SPIFFS
  File root = SPIFFS.open("/");
  if (root) {
    File file = root.openNextFile();
    while (file) {
      String filename = file.name();
      if (filename.startsWith("/offline_") && filename.endsWith(".json")) {
        count++;
      }
      file = root.openNextFile();
    }
    root.close();
  }
  
  // Count entries in preferences
  for (int i = 0; i < 10; i++) {
    String key = "offline" + String(i);
    String data = preferences.getString(key.c_str(), "");
    if (data.length() > 0) {
      count++;
    }
  }
  
  return count;
}

void clearAllOfflineData() {
  Serial.println("Clearing all offline data...");
  
  // Clear SPIFFS files
  File root = SPIFFS.open("/");
  if (root) {
    File file = root.openNextFile();
    while (file) {
      String filename = file.name();
      if (filename.startsWith("/offline_") && filename.endsWith(".json")) {
        file.close();
        if (SPIFFS.remove(filename)) {
          Serial.println("Deleted: " + filename);
        }
      }
      file = root.openNextFile();
    }
    root.close();
  }
  
  // Clear preferences
  for (int i = 0; i < 10; i++) {
    String key = "offline" + String(i);
    preferences.remove(key.c_str());
  }
  
  // Reset counter
  offlineRecordCount = 0;
  preferences.putInt("offlineCount", 0);
  
  Serial.println("All offline data cleared");
}

// Web Server Handlers
void handleRoot() {
  if (!authenticate()) return;
  
  String html = generateDashboardHTML();
  server.send(200, "text/html", html);
}

void handleApiStatus() {
  if (!authenticate()) return;
  
  DynamicJsonDocument doc(1024);
  doc["deviceId"] = "ESP32-Beehive-001";
  doc["uptime"] = millis() / 1000;
  doc["freeHeap"] = ESP.getFreeHeap();
  doc["wifiConnected"] = wifiConnected;
  doc["wifiSSID"] = WiFi.SSID();
  doc["ipAddress"] = WiFi.localIP().toString();
  doc["gateway"] = WiFi.gatewayIP().toString();
  doc["subnetMask"] = WiFi.subnetMask().toString();
  doc["dnsServer"] = WiFi.dnsIP(0).toString();
  doc["macAddress"] = WiFi.macAddress();
  doc["signalStrength"] = WiFi.RSSI();
  doc["offlineRecords"] = offlineRecordCount;
  doc["actualOfflineRecords"] = countActualOfflineRecords();
  doc["readingCount"] = readingCount;
  doc["maxReadings"] = MAX_READINGS;
  doc["readingInterval"] = READING_INTERVAL / 1000;
  
  // Get latest sensor reading
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  doc["currentTemperature"] = isnan(temp) ? "N/A" : String(temp);
  doc["currentHumidity"] = isnan(hum) ? "N/A" : String(hum);
  doc["lastReading"] = getCurrentTimestamp();
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleApiData() {
  if (!authenticate()) return;
  
  // Get recent sensor data (simple version)
  DynamicJsonDocument doc(2048);
  JsonArray dataArray = doc.createNestedArray("data");
  
  // Add current reading
  JsonObject current = dataArray.createNestedObject();
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  current["timestamp"] = getCurrentTimestamp();
  current["temperature"] = isnan(temp) ? 0 : temp;
  current["humidity"] = isnan(hum) ? 0 : hum;
  current["status"] = !isnan(temp) && !isnan(hum);
  
  doc["count"] = dataArray.size();
  doc["status"] = "success";
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleApiOffline() {
  if (!authenticate()) return;
  
  DynamicJsonDocument doc(1024);
  doc["offlineRecords"] = offlineRecordCount;
  doc["actualCount"] = countActualOfflineRecords();
  
  // List offline files
  JsonArray files = doc.createNestedArray("files");
  File root = SPIFFS.open("/");
  if (root) {
    File file = root.openNextFile();
    while (file) {
      String filename = file.name();
      if (filename.startsWith("/offline_") && filename.endsWith(".json")) {
        JsonObject fileObj = files.createNestedObject();
        fileObj["name"] = filename;
        fileObj["size"] = file.size();
      }
      file = root.openNextFile();
    }
    root.close();
  }
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleApiClear() {
  if (!authenticate()) return;
  
  clearAllOfflineData();
  
  DynamicJsonDocument doc(256);
  doc["status"] = "success";
  doc["message"] = "All offline data cleared";
  doc["offlineRecords"] = offlineRecordCount;
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleApiSend() {
  if (!authenticate()) return;
  
  if (!wifiConnected) {
    server.send(400, "application/json", "{\"status\":\"error\",\"message\":\"No WiFi connection\"}");
    return;
  }
  
  int previousCount = offlineRecordCount;
  sendOfflineData();
  
  DynamicJsonDocument doc(256);
  doc["status"] = "success";
  doc["message"] = "Send attempt completed";
  doc["previousCount"] = previousCount;
  doc["currentCount"] = offlineRecordCount;
  doc["sent"] = previousCount - offlineRecordCount;
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleApiReboot() {
  if (!authenticate()) return;
  
  server.send(200, "application/json", "{\"status\":\"success\",\"message\":\"Rebooting in 3 seconds\"}");
  delay(3000);
  ESP.restart();
}

void handleNotFound() {
  server.send(404, "text/plain", "404 Not Found");
}

bool authenticate() {
  if (!server.authenticate(webUsername.c_str(), webPassword.c_str())) {
    server.requestAuthentication();
    return false;
  }
  return true;
}

String generateDashboardHTML() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Beehive Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; margin: 20px; background: #f0f8ff; }
        .container { max-width: 800px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(45deg, #ff6b35, #f7931e); color: white; text-align: center; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-box { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #333; }
        .stat-label { color: #666; font-size: 14px; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-warning { background: #ffc107; color: black; }
        .btn-danger { background: #dc3545; color: white; }
        .btn:hover { opacity: 0.8; }
        .online { color: #28a745; }
        .offline { color: #dc3545; }
        #log { background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 12px; max-height: 300px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card header">
            <h1>ESP32 Beehive Monitor</h1>
            <p>Remote Monitoring Dashboard</p>
        </div>
        
        <div class="card">
            <h2>System Status</h2>
            <div class="status-grid" id="statusGrid">
                <div class="stat-box">
                    <div class="stat-value" id="wifiStatus">Loading...</div>
                    <div class="stat-label">WiFi Status</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="temperature">-°C</div>
                    <div class="stat-label">Temperature</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="humidity">-%</div>
                    <div class="stat-label">Humidity</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="uptime">0s</div>
                    <div class="stat-label">Uptime</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="offlineRecords">0</div>
                    <div class="stat-label">Offline Records</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="freeHeap">0 KB</div>
                    <div class="stat-label">Free Memory</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Controls</h2>
            <button class="btn btn-primary" onclick="sendOfflineData()">Send Offline Data</button>
            <button class="btn btn-warning" onclick="clearOfflineData()">Clear Offline Data</button>
            <button class="btn btn-primary" onclick="refreshData()">Refresh</button>
            <button class="btn btn-danger" onclick="rebootDevice()">Reboot ESP32</button>
        </div>
        
        <div class="card">
            <h2>Activity Log</h2>
            <div id="log"></div>
        </div>
    </div>

    <script>
        function log(message) {
            const logDiv = document.getElementById('log');
            const timestamp = new Date().toLocaleTimeString();
            logDiv.innerHTML += '[' + timestamp + '] ' + message + '\n';
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('wifiStatus').textContent = data.wifiConnected ? 'Online' : 'Offline';
                    document.getElementById('wifiStatus').className = 'stat-value ' + (data.wifiConnected ? 'online' : 'offline');
                    
                    document.getElementById('temperature').textContent = data.currentTemperature + '°C';
                    document.getElementById('humidity').textContent = data.currentHumidity + '%';
                    document.getElementById('uptime').textContent = formatUptime(data.uptime);
                    document.getElementById('offlineRecords').textContent = data.offlineRecords;
                    document.getElementById('freeHeap').textContent = Math.round(data.freeHeap / 1024) + ' KB';
                })
                .catch(error => {
                    log('Error fetching status: ' + error.message);
                });
        }

        function sendOfflineData() {
            log('Sending offline data...');
            fetch('/api/send', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    log(data.message + ' - Sent: ' + data.sent + ' records');
                    updateStatus();
                })
                .catch(error => {
                    log('Error sending data: ' + error.message);
                });
        }

        function clearOfflineData() {
            if (confirm('Are you sure you want to clear all offline data?')) {
                log('Clearing offline data...');
                fetch('/api/clear', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        log(data.message);
                        updateStatus();
                    })
                    .catch(error => {
                        log('Error clearing data: ' + error.message);
                    });
            }
        }

        function rebootDevice() {
            if (confirm('Are you sure you want to reboot the ESP32?')) {
                log('Rebooting device...');
                fetch('/api/reboot', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        log(data.message);
                        setTimeout(() => {
                            log('Device should be rebooting now...');
                        }, 3000);
                    })
                    .catch(error => {
                        log('Error rebooting: ' + error.message);
                    });
            }
        }

        function refreshData() {
            log('Refreshing data...');
            updateStatus();
        }

        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            
            if (days > 0) return days + 'd ' + hours + 'h';
            if (hours > 0) return hours + 'h ' + minutes + 'm';
            return minutes + 'm';
        }

        // Auto-refresh every 30 seconds
        setInterval(updateStatus, 30000);
        
        // Initial load
        updateStatus();
        log('Dashboard loaded successfully');
    </script>
</body>
</html>
)rawliteral";
  
  return html;
}

void printSystemInfo() {
  Serial.println("ESP32 System Information:");
  Serial.println("   Free Heap: " + String(ESP.getFreeHeap()) + " bytes");
  Serial.println("   WiFi Status: " + String(wifiConnected ? "Connected" : "Disconnected"));
  Serial.println("   Offline Records: " + String(offlineRecordCount));
  Serial.println("   Uptime: " + String(millis() / 1000) + " seconds");
  
  if (wifiConnected) {
    Serial.println("   IP Address: " + WiFi.localIP().toString());
    Serial.println("   Signal Strength: " + String(WiFi.RSSI()) + " dBm");
  }
}