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
#include <fusekit/stream_callback_file.h>
#include <thread>
#include <functional>
#include <boost/regex.hpp>
#include "RF24.h"
#include "../car_firmware/protocol.h"

using namespace std;
using namespace boost;

#define NUM_RETRIES 15  // Number of retries with no response tolerated
                        // until loss-of-connection is declared

#define CONTROL_REGEX  "@(-?[[:digit:]]{1,3}),(-?[[:digit:]]{1,3})"

#define SPEED_MIN -127
#define SPEED_MAX 127
#define ROT_MIN -127
#define ROT_MAX 127

#define NOT_CONNECTED "not_connected"

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

  void set_speed(int _speed) {
    if ((_speed >= SPEED_MIN) && (_speed <= SPEED_MAX))
      speed = _speed;
  }

  void set_rot(int _rot) {
    if ((_rot >= ROT_MIN) && (_rot <= ROT_MAX))
      rot = _rot;
  }

  void set_leds(uint8_t _leds) {
    leds = _leds;
  }

  bool is_connected() const {
    return connected;
  }

  bool is_running() const {
    return running;
  }

  int get_battery() const {
    return battery;
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
    running = false;
    loop_running = false;
    speed = 0;
    rot = 0;
    leds = 0;
  }

  bool init() {
    return nrf_init();
  }

  void run() {
    while(loop_running) {
      msg_to_car.speed = speed;
      msg_to_car.rot = rot;
      msg_to_car.leds = leds;

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
	  running = inmsg->running;
	  battery = inmsg->battery;

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

    speed = 0;
    rot = 0;
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
  bool running;
  uint8_t battery;
  int retries;
  msg_from_car_t* inmsg;
  int speed;
  int rot;
  uint8_t leds;

};

carlink* carlink::instance = NULL;

/// control virtual file implementation
///////////////////////////////////////


struct control_file: 
  public fusekit::iostream_object_file<control_file>::type {

  control_file(carlink& _car) : 
    fusekit::iostream_object_file<control_file>::type(*this),
    control_fmt(CONTROL_REGEX, regex::perl),
    car(_car)
  {}

  int open(fuse_file_info& fi) {
    carlink::get_instance().start();
    return fusekit::iostream_object_file<control_file>::type::open(fi);
  }

  int write(const char* src, size_t size, 
	    off_t offset, struct fuse_file_info& fi) {

    // Write the new data into the file. We assume always-append,
    // so the offset argument is ignored
    buf += src;

    // Look for the end-of-line delimiter(s)
    size_t i;
    while((i = buf.find('\n')) != string::npos) {

      // Delimiter found - chop the string into two parts - before
      // the delimiter (for processing) and after the delimiter
      if (i > 0) {
	string line = buf.substr(0, i);
	parse(line);
      }

      // Store the rest of the string back in the buffer
      buf = buf.substr(i+1);
    }

    return size;
  }

  int release(fuse_file_info& fi) {
    carlink::get_instance().stop();
    return fusekit::iostream_object_file<control_file>::type::release(fi);
  }

  void parse(string& line) {
    //cout << "got a line: " << line << endl;;
    smatch match;
    if (regex_match(line, match, control_fmt) && match.size() > 1) {

      int speed = stoi(match.str(1));
      int rot = stoi(match.str(2));

      car.set_speed(speed);
      car.set_rot(rot);

      //cout << "match speed=" << speed << " rot=" << rot << endl;
    }
    else {
      //cout << "no match" << endl;
    }
  }

  regex control_fmt;
  string buf;
  carlink& car;
};

std::ostream& operator<<(std::ostream& os, const control_file& f)
{
  return os;
}

std::istream& operator>>(std::istream& is, control_file& f) {
  return is;
}


// Functions to read the car state
// and convert it to strings
int f_is_connected(ostream& os) {
  carlink& car = carlink::get_instance();
  os << car.is_connected();
  return 0;
}

int f_is_running(ostream& os) {
  carlink& car = carlink::get_instance();
  if (!car.is_connected())
    os << NOT_CONNECTED;
  else
    os << car.is_running();

  return 0;
}

int f_battery(ostream& os) {
  carlink& car = carlink::get_instance();
  if (!car.is_connected())
    os << NOT_CONNECTED;
  else
    os << car.get_battery();

  return 0;
}

int main( int argc, char* argv[] ){

  cout << "running" << endl;
  //if (!car.init())
  //  return -1;

  //car.run();

  carlink& car = carlink::get_instance();

  fusekit::daemon<>& daemon = fusekit::daemon<>::instance();
  daemon.root().add_file("control", new control_file(car)); 
  daemon.root().add_file("connected", 
	 fusekit::make_ostream_callback_file(f_is_connected));
  daemon.root().add_file("running", 
	 fusekit::make_ostream_callback_file(f_is_running));
  daemon.root().add_file("battery", 
	 fusekit::make_ostream_callback_file(f_battery));

  return daemon.run(argc,argv);


}
