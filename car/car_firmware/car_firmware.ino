#include <SPI.h>
#include <RF24.h>
#include <Wire.h>
#include "BH1750.h"
#include "protocol.h"

#define LEFT_PWM   6
#define LEFT_DIR   8
#define RIGHT_PWM  5
#define RIGHT_DIR  4
#define LED1       2
#define LED2       7
#define SUCTION    3
#define NRF_CE     9
#define NRF_CSN    10
#define BAT_SENSE  2

// Dilution of debug print messages
#define DILUTE 100

// The timeout (in mS) after which the car is considered disconnected
#define MSG_TIMEOUT 200

// Light sensor constants
#define LIGHT_SAMPLE_RATE_DIVIDER 100
#define DARK_THRESHOLD 2

// Number of battery samples for averaging
#define BATTERY_SAMPLES 8

// ce,csn pins
RF24 radio(NRF_CE, NRF_CSN);

union {
  char raw[32];
  msg_to_car_t msg;
} inbuf;

msg_from_car_t msg_from_car;
bool connected;
unsigned long last_msg_time;
bool running;
int8_t speed;
int8_t rot;
uint8_t leds;
int motor_left;
int motor_right;
uint8_t debug_dilute;
BH1750 light_sensor;
int light_sensor_samp;
int battery_level;
unsigned long battery_sum;
uint8_t battery_count;
 
void setup(void)
{
  // Inputs and outputs
  pinMode(LEFT_PWM, OUTPUT);
  pinMode(LEFT_DIR, OUTPUT);
  pinMode(RIGHT_PWM, OUTPUT);
  pinMode(RIGHT_DIR, OUTPUT);
  pinMode(SUCTION, OUTPUT);

  digitalWrite(LEFT_PWM, LOW);
  digitalWrite(RIGHT_PWM, LOW);
  digitalWrite(SUCTION, HIGH);

  msg_from_car.magic1 = MAGIC1;
  msg_from_car.magic2 = MAGIC2;

  // Init variables
  connected = false;
  last_msg_time = millis();
  running = false;
  speed = 0;
  rot = 0;
  motor_left = 0;
  motor_right = 0;
  debug_dilute = DILUTE;
  battery_level = 0;
  battery_count = BATTERY_SAMPLES;
  battery_sum = 0;
  
  // Init serial
  Serial.begin(57600);

  // Init light sensor
  light_sensor.begin();
  light_sensor_samp = LIGHT_SAMPLE_RATE_DIVIDER;

  // init radio
  radio.begin();
  radio.setPALevel(RF24_PA_MAX);
  radio.setDataRate(RF24_1MBPS);
  radio.setCRCLength(RF24_CRC_16);
  radio.setChannel(NRF_CHANNEL);
  radio.openReadingPipe(1, NRF_PI_ADDR);
  radio.openWritingPipe(NRF_CAR_ADDR);
  radio.enableDynamicPayloads();
  radio.setAutoAck(0);
  radio.powerUp();
  radio.startListening();
}

void loop(void)
{
    if (radio.available()) {    
      // Read the packet
      uint8_t size = radio.getDynamicPayloadSize();
      if (size > 32)
        size = 32;
      radio.read((void*)&inbuf, size);
      
      // Validate it
      if ((size == sizeof(msg_to_car_t)) &&
          (inbuf.msg.magic1 == MAGIC1) &&
          (inbuf.msg.magic2 == MAGIC2)) {

            // We are connected
            connected = 1;
            last_msg_time = millis();
            
            // Set speed, rotation and leds
            speed = inbuf.msg.speed;
            rot = inbuf.msg.rot;
            leds = inbuf.msg.leds;

            // Valid message
            msg_from_car.serial = inbuf.msg.serial;
            msg_from_car.battery = battery_level/2;
            msg_from_car.running = running;

            radio.stopListening();
            radio.write((const void*)&msg_from_car, sizeof(msg_from_car_t));
            radio.startListening();
          }         
    }
    else {
      // No message available
      if ((millis() - last_msg_time) > MSG_TIMEOUT) {
        // Too much time passed since last message - declare no connect
        // and stop any motion
        connected= 0;
        speed = 0;
        rot = 0;
      }
    }
    
    // Print debug message
    if (debug_dilute == 0) {
      debug_dilute = DILUTE;
      
      static char debug_message[120];
      sprintf(debug_message, "ser=%d conn=%d run=%d spd=%d rot=%d left=%d right=%d bat=%d\n",
        inbuf.msg.serial, connected, running, speed, rot, motor_left, motor_right, battery_level);
      Serial.print(debug_message);
      //radio.printDetails();

    }
    else
      debug_dilute--;

    // Light sensor + battery sample
    if (light_sensor_samp == 0) {
      light_sensor_samp = LIGHT_SAMPLE_RATE_DIVIDER;

      // Get a light sensor sample
      uint16_t ll = light_sensor.readLightLevel();
      if (ll <= DARK_THRESHOLD) {
        running = 1;
        digitalWrite(SUCTION, LOW);
      }
      else {
        running = 0;
        digitalWrite(SUCTION, HIGH);
      }

      // Battery - average several readings to get more stable result
      battery_sum += analogRead(BAT_SENSE);
      battery_count--;

      if (battery_count == 0) {
        battery_level = battery_sum / BATTERY_SAMPLES;
        battery_sum = 0;
        battery_count = BATTERY_SAMPLES;
      }
      battery_level = analogRead(BAT_SENSE);
      
    }
    else
      light_sensor_samp--;

}
