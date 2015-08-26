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
#include <iostream>
#include <fusekit/daemon.h>
#include <fusekit/stream_object_file.h>
#include <thread>
#include "RF24.h"
#include "../car_firmware/protocol.h"

using namespace std;

#define NUM_RETRIES 15  // Number of retries with no response tolerated
                        // until loss-of-connection is declared

class carlink {

public:
  static carlink& get_instance() {
    if (instance == NULL) {
      instance = new carlink();
      instance->init();
    }
    return *instance;
  }

  void start() {

    // Create a thread
    loop_running = true;
    loop_thread = new thread([this]() { this->run(); });
  }

  void stop() {
    if (loop_running) {
      loop_running = false;
      loop_thread->join();
    }
  }


protected:
  carlink(): 
    radio(RPI_V2_GPIO_P1_15, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ) {
    msg_to_car.magic1 = MAGIC1;
    msg_to_car.magic2 = MAGIC2;
    serial = 0;
    retries = 0;
    inmsg = (msg_from_car_t*)buf;
    connected = false;
    loop_running = false;
  }

  bool init() {
    return nrf_init();
  }

  void run() {
    while(loop_running) {
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

protected:
  static carlink* instance;
  thread* loop_thread;
  bool loop_running;
  RF24 radio;
  msg_to_car_t msg_to_car;
  msg_from_car_t msg_from_car;
  uint16_t serial;
  uint8_t buf[32];
  bool connected;
  int retries;
  msg_from_car_t* inmsg;

};

carlink* carlink::instance = NULL;

/// control virtual file implementation
///////////////////////////////////////


struct control_file: 
  public fusekit::iostream_object_file<control_file>::type {

  control_file() : fusekit::iostream_object_file<control_file>::type(*this)
  {}

  int open(fuse_file_info& fi) {
    carlink::get_instance().start();
    return fusekit::iostream_object_file<control_file>::type::open(fi);
  }

  int release(fuse_file_info& fi) {
    carlink::get_instance().stop();
    return fusekit::iostream_object_file<control_file>::type::release(fi);
  }

};

std::ostream& operator<<(std::ostream& os, const control_file& f)
{
  return os;
}

std::istream& operator>>(std::istream& is, control_file& f) {
  return is;
}



int main( int argc, char* argv[] ){

  //if (!car.init())
  //  return -1;

  //car.run();


  fusekit::daemon<>& daemon = fusekit::daemon<>::instance();
  daemon.root().add_file("control", new control_file); 

  return daemon.run(argc,argv);
}
