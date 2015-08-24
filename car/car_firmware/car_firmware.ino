#include <SPI.h>
#include <RF24.h>
#include "protocol.h"
 
// ce,csn pins
RF24 radio(7,8);
 
void setup(void)
{
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

char inbuf[32];
 
void loop(void)
{

    if (radio.available()) {
      Serial.println("got something");
      
      uint8_t size = radio.getDynamicPayloadSize();
      if (size > 32)
        size = 32;
      radio.read(inbuf, size);
    }
    //radio.printDetails();

}
