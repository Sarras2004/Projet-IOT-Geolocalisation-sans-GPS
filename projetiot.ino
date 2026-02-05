#include <HardwareSerial.h>
#include <WiFi.h>

// --- Configuration des PINs ---
#define RX_PIN 16
#define TX_PIN 17

// --- Tes Identifiants TTN ---
const String DevEUI = "70B3D57ED0074BC5";
const String AppEUI = "0000000000000000";
const String AppKey = "E2E7986AB6F822958EB2BFE93C4A9705";

HardwareSerial LoRaSerial(2);

// Fonction pour lire la réponse du module proprement
String readLoRaResponse(int timeoutMs = 2000) {
  String response = "";
  long start = millis();
  while (millis() - start < timeoutMs) {
    while (LoRaSerial.available()) {
      char c = LoRaSerial.read();
      response += c;
    }
  }
  return response;
}

void sendATCommand(String cmd, int waitTime = 1000) {
  Serial.println("CMD: " + cmd);
  LoRaSerial.println(cmd);
  String response = readLoRaResponse(waitTime);
  Serial.print("REPONSE MODULE: ");
  Serial.println(response);
}

void setup() {
  Serial.begin(115200);
  while (!Serial);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  Serial.println(">>> Initialisation LoRaWAN <<<");
  LoRaSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN); // Vérifie si ton module n'est pas en 115200 !
  delay(1000);

  // Configuration de base
  sendATCommand("AT");
  sendATCommand("AT+ID=DevEui," + DevEUI);
  sendATCommand("AT+ID=AppEui," + AppEUI);
  sendATCommand("AT+KEY=APPKEY," + AppKey);
  sendATCommand("AT+DR=EU868");
  sendATCommand("AT+CH=NUM,0-2");

  // --- BOUCLE DE CONNEXION ROBUSTE ---
  bool isJoined = false;
  while (!isJoined) {
    Serial.println(">>> Tentative de connexion au réseau (JOIN)...");
    LoRaSerial.println("AT+JOIN");
    
    // On attend la réponse du module pendant 10 secondes
    String response = readLoRaResponse(10000);
    Serial.println(response);

    // On analyse la réponse pour voir si c'est bon
    if (response.indexOf("Joined") != -1 || response.indexOf("Network joined") != -1 || response.indexOf("Already joined") != -1) {
      isJoined = true;
      Serial.println(">>> SUCCÈS : Connecté au réseau LoRaWAN ! <<<");
    } else {
      Serial.println(">>> ECHEC : Pas encore connecté, nouvelle tentative dans 5s...");
      delay(5000);
    }
  }
}

void loop() {
  Serial.println("\n--- Nouveau Cycle de Scan (Toutes les 20s) ---");
  
  int n = WiFi.scanNetworks();
  
  if (n > 0) {
    String payloadHex = "";
    int limit = (n < 3) ? n : 3; 

    for (int i = 0; i < limit; i++) {
      uint8_t* mac = WiFi.BSSID(i);
      
      // Conversion MAC propre
      char macStr[13];
      sprintf(macStr, "%02X%02X%02X%02X%02X%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
      
      // Conversion RSSI (Valeur absolue pour simplifier)
      int32_t rssi = WiFi.RSSI(i);
      uint8_t rssiByte = (uint8_t) abs(rssi); 
      char rssiHex[3];
      sprintf(rssiHex, "%02X", rssiByte);
      
      payloadHex += String(macStr) + String(rssiHex);
    }

    // Bourrage avec des 0 si moins de 3 réseaux pour garder la taille fixe
    while (payloadHex.length() < 42) {
      payloadHex += "00";
    }

    Serial.println("Payload à envoyer: " + payloadHex);
    
    // Envoi de la donnée
    // On augmente le délai de lecture à 5s pour laisser le temps au module de dire "Done"
    sendATCommand("AT+CMSGHEX=\"" + payloadHex + "\"", 5000);
  } else {
    Serial.println("Aucun réseau WiFi trouvé.");
  }

  WiFi.scanDelete();

  // ATTENTE DE 20 SECONDES
  Serial.println("Attente de 20 secondes...");
  delay(20000); 
}

