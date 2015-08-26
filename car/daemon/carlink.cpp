// The nRF is assumed to be connected to the Pi in
// the following manner (pin numbers relate to RPi 2):
//
// RPi Pin    nRF Pin
// -------    -------
//   21       MISO
//   19       MOSI
//   23       SCK
//   24       CSN
//   22       CE
//    1       VCC (or any other 3.3V supply)
//    3       GND (or any other ground)

#include <unistd.h>
#include <fusekit/daemon.h>
#include <fusekit/stream_callback_file.h>
#include <iostream>
#include "RF24.h"
#include "../car_firmware/protocol.h"

using namespace std;

#define NUM_RETRIES 15  // Number of retries with no response tolerated
                        // until loss-of-connection is declared

class carlink {

public:
  carlink(): 
    radio(RPI_V2_GPIO_P1_15, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ) {
    msg_to_car.magic1 = MAGIC1;
    msg_to_car.magic2 = MAGIC2;
    serial = 0;
    retries = 0;
    inmsg = (msg_from_car_t*)buf;
    connected = false;
  }

  bool init() {
    return nrf_init();
  }

  void run() {
    while(1) {
      // TODO: Fill the real values here
      msg_to_car.speed = 0;
      msg_to_car.rot = 0;
      msg_to_car.leds = 0;

      // Send the message
      msg_to_car.serial = serial++;
      radio.write((const void*)&msg_to_car, sizeof(msg_to_car_t));

      // Turn on listening, waiting for response
      radio.startListening();

      // Sleep for ~10mS
      usleep(10*1000);

      // Check for response
      if (radio.available()) {
       int size = radio.getDynamicPayloadSize();
	radio.read(buf, size);
      
	// Validate the packet
	if ((size == sizeof(msg_from_car_t)) &&
	    (inmsg->magic1 == MAGIC1) &&
	    (inmsg->magic2 == MAGIC2) &&
	    (inmsg->serial == (serial - 1))) {
	  // Valid packet
	      
	  // Switch to connected state
	  connected = true;	      retries = NUM_RETRIES;

	}
	else {
	  // Invalid packet
	  if (retries > 0)
	    retries--;
	}
      }
      else {
	if (retries > 0)
	  retries--;
      }

      if (retries == 0) {
	connected = false;
      }
      cout << connected << endl;

      radio.stopListening();
    }
  }
  
protected:
  bool nrf_init()
  {
    // init radio for reading
    if (!radio.begin()) {
      cerr << "nRF begin() failed" << endl;
      return false;
    }
    
    radio.enableDynamicPayloads();
    radio.setAutoAck(0);
    radio.setDataRate(RF24_1MBPS);
    radio.setPALevel(RF24_PA_MAX);
    radio.setChannel(NRF_CHANNEL);
    radio.setCRCLength(RF24_CRC_16);
    radio.openReadingPipe(1, NRF_CAR_ADDR);
    radio.openWritingPipe(NRF_PI_ADDR);
    radio.powerUp();

#ifdef DEBUG
    radio.printDetails();
#endif

    return true;
  }

  RF24 radio;
  msg_to_car_t msg_to_car;
  msg_from_car_t msg_from_car;
  uint16_t serial;
  uint8_t buf[32];
  bool connected;
  int retries;
  msg_from_car_t* inmsg;

};

  carlink car;


/// free function which will be called
/// when the virtual file "hello.txt" is read
int hello( std::ostream& os ){
  os << "hello world!";
  return 0;
}

/// example which demonstrates how to expose
/// data through a free function callback.
/// after program has been started (see below)
/// you can find a single file called hello.txt within
/// the mountpoint/mount-directory. try to read it
/// with cat( e.g. cat hello_mnt/hello.txt).
/// 
/// start from shell like this:
/// $ mkdir hello_mnt
/// $ hellofs hello_mnt
int main( int argc, char* argv[] ){
  if (!car.init())
    return -1;

  car.run();

  /*
  fusekit::daemon<>& daemon = fusekit::daemon<>::instance();
  daemon.root().add_file(
			 "hello.txt", 
			 /// create an ostream_callback_file instance
			 /// with auto deduced template parameters
			 fusekit::make_ostream_callback_file(hello)
			 );
  /// runs the daemon at the mountpoint specified in argv
  /// and with other options if specified
  return daemon.run(argc,argv);
  */



  return 0;
}
