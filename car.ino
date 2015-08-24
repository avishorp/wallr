#include <SPI.h>
#include <RF24.h>
 
// ce,csn pins
RF24 radio(7,8);
 
// init counter
unsigned long count = 55;
 
void setup(void)
{
  Serial.begin(57600);
    // init radio for writing on channel 76
    radio.begin();


    radio.setPALevel(RF24_PA_MAX);
    radio.setDataRate(RF24_1MBPS);
    radio.setCRCLength(RF24_CRC_16);
    radio.setChannel(0x4c);
    //radio.openReadingPipe(0,0xF0F0F0F0E1LL);
    radio.openReadingPipe(0,0x65646f4e32LL);
    radio.openWritingPipe(0xF0F0F0F0E1LL);
    radio.enableDynamicPayloads();
    radio.setAutoAck(0);
    radio.setRetries(15,15);
    radio.powerUp();
    delay(2000);
    Serial.println("Go!");
    radio.printDetails();
}

    char outBuffer[32]= "                  ";
 
void loop(void)
{
  while(1){

    // 32 bytes is maximum payload
 
    // pad numbers and convert to string
    sprintf(outBuffer,"data=%2d",count);
 
    // transmit and increment the counter
    bool ok  = radio.write(outBuffer, 12);
    if (ok)
      Serial.println("write ok");
    else
      Serial.println("write fail");
    if (radio.isAckPayloadAvailable()) {
      Serial.println("ack");
    }
    count++;

radio.startListening();
  Serial.println(outBuffer); 
  radio.printDetails();
    // pause a second
    //radio.powerDown();
    //radio.powerUp();
    delay(1000);
    radio.stopListening();
  }
}
