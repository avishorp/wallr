// Car <--> RPi link protocol

#include <ctype.h>

// The magic numbers appear at the beginning of
// each message (packet). Just to make sure that
// this packet is not a random garbage

#define MAGIC1  0x53
#define MAGIC2  0xf0

// RPi --> Car
typedef struct {
  uint8_t magic1;  // Must be equal to MAGIC1
  uint8_t magic2;  // Must be equal to MAGIC2
  uint8_t speed;   // Speed (0-127)
  uint8_t rot;     // Rotation (-32 to +32)
  uint8_t leds;    // LED status (bitmapped)
} msg_to_car_t;

// Car --> RPi
typedef struct {
  uint8_t magic1;  // Must be equal to MAGIC1
  uint8_t magic2;  // Must be equal to MAGIC2
  uint8_t battery; // Battery status
  uint8_t running; // Non-zero if the car is running
} msg_from_car_t;

#define NRF_CHANNEL   76  // The RF channel
#define NRF_PI_ADDR   0xF0F0F0F011LL
#define NRF_CAR_ADDR  0xF0F0F0F022LL
