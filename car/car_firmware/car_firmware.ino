#include <SPI.h>
#include <RF24.h>
#include "protocol.h"
 
// ce,csn pins
RF24 radio(7,8);

union {
  char raw[32];
  msg_to_car_t msg;
} inbuf;

msg_from_car_t msg_from_car;
 
void setup(void)
{
  msg_from_car.magic1 = MAGIC1;
  msg_from_car.magic2 = MAGIC2;
  
  // Init serial
  Serial.begin(57600);

  // init radio
  radio.begin();
  radio.setPALevel(RF24_PA_MAX);
  radio.setDataRate(RF24_1MBPS);
  radio.setCRCLength(RF24_CRC_16);
  radio.setChannel(NRF_CHANNEL);
  radio.openReadingPipe(1, NRF_PI_ADDR);
  //radio.openWritingPipe(NRF_CAR_ADDR);
  radio.enableDynamicPayloads();
  radio.setAutoAck(0);
  radio.powerUp();
  radio.startListening();
}

void loop(void)
{

    if (radio.available()) {
      Serial.println("got something");
      
      // Read the packet
      uint8_t size = radio.getDynamicPayloadSize();
      if (size > 32)
        size = 32;
      radio.read((void*)&inbuf, size);
      
      // Validate it
      if ((size == sizeof(msg_to_car_t)) &&
          (inbuf.msg.magic1 == MAGIC1) &&
          (inbuf.msg.magic2 == MAGIC2)) {

            Serial.println("valid");

            // Valid message
            msg_from_car.serial = inbuf.msg.serial;
            
            radio.stopListening();
            radio.write((const void*)&msg_from_car, sizeof(msg_from_car_t));
            radio.startListening();
          }
          
      else
          Serial.println(size, DEC);
    }
    //radio.printDetails();

}
