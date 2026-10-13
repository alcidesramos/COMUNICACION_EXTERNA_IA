#include <Arduino.h>
#include <DHT.h>

#define POT_PIN 4
#define DHT_PIN 15
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  dht.begin();
  Serial.println("ESP32 DevKit V1 - Potenciometro + DHT22");
}

void loop() {
  int raw = analogRead(POT_PIN);
  float porcentaje = raw *3.3 / 4095 ;
  float temperatura = dht.readTemperature();
  float humedad = dht.readHumidity();

  Serial.printf("Pot: %d (%.1f%%)", raw, porcentaje);
  if (isnan(temperatura) || isnan(humedad)) {
    Serial.println(" | Error leyendo DHT22");
  } else {
    Serial.printf(" | Temp: %.1f C | Hum: %.1f %%\n", temperatura, humedad);
  }

  delay(2000);
}
