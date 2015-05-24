/*
 * ArduinoNunchukDemo.ino
 *
 * Copyright 2011-2013 Gabriel Bianconi, http://www.gabrielbianconi.com/
 *
 * Project URL: http://www.gabrielbianconi.com/projects/arduinonunchuk/
 *
 */

#include <Wire.h>
#include <ArduinoNunchuk.h>

#define BAUDRATE 19200
#define LEFT_PWM 10
#define LEFT_DIR 14
#define RIGHT_PWM 11
#define RIGHT_DIR 15
#define LED1 8
#define LED2 9

#define DEAD_ZONE_X 10
#define DEAD_ZONE_Y 10

ArduinoNunchuk nunchuk = ArduinoNunchuk();

void setup()
{
  // Initialize all pins
  pinMode(LEFT_PWM, OUTPUT);
  pinMode(LEFT_DIR, OUTPUT);
  pinMode(RIGHT_PWM, OUTPUT);
  pinMode(RIGHT_DIR, OUTPUT);
  analogWrite(LEFT_PWM, 0);
  analogWrite(RIGHT_PWM, 0);
  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  digitalWrite(LED1, HIGH);
  digitalWrite(LED2, HIGH);

  Serial.begin(BAUDRATE);
  nunchuk.init();
}


void loop()
{
  nunchuk.update();

  Serial.print(nunchuk.analogX, DEC);
  Serial.print(' ');
  Serial.print(nunchuk.analogY, DEC);
  Serial.print(' ');
  Serial.print(nunchuk.accelX, DEC);
  Serial.print(' ');
  Serial.print(nunchuk.accelY, DEC);
  Serial.print(' ');
  Serial.print(nunchuk.accelZ, DEC);
  Serial.print(' ');
  Serial.print(nunchuk.zButton, DEC);
  Serial.print(' ');
  Serial.println(nunchuk.cButton, DEC);
  
  if (!((nunchuk.accelX == 512) && (nunchuk.accelY == 512) && (nunchuk.accelZ == 684))) {
    // Data available
    digitalWrite(LED1, LOW);
    digitalWrite(LED2, LOW);    

    int x = nunchuk.analogX - 128;
    int y = nunchuk.analogY - 128;

    if (!((x > DEAD_ZONE_X) || (x < -DEAD_ZONE_X)))
      x = 0;
    if (!((y > DEAD_ZONE_Y) || (y < -DEAD_ZONE_Y)))
      y = 0;
      
    int forward = y;
    int rotate = x;
    
    int left = forward;
    int right = forward;
    
    right += (rotate/2 );
    left -= (rotate /2); 
    
    // Clamp the values
    left = ((left > 127)?  127 : ((left < -127)? -127 : left));
    right = ((right > 127)?  127 : ((right < -127)? -127 : right));
    
//    left += left/2;
//    right += right/2;
    
    // Drive left motor
    if (left > 0) {
      digitalWrite(LEFT_DIR, 1);
      analogWrite(LEFT_PWM, left);
    }
    else {
      digitalWrite(LEFT_DIR, 0);
      analogWrite(LEFT_PWM, -left);
    }
    
    // Drive right motor
    if (right > 0) {
      digitalWrite(RIGHT_DIR, 0);
      analogWrite(RIGHT_PWM, right);
    }
    else {
      digitalWrite(RIGHT_DIR, 1);
      analogWrite(RIGHT_PWM, -right);
    }
    
    
  }
  else {
    // Disconnected
    digitalWrite(LED1, HIGH);    
    digitalWrite(LED2, HIGH);    
    analogWrite(LEFT_PWM, 0);
    analogWrite(RIGHT_PWM, 0);
  }

}
