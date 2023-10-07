#include <Servo.h>

Servo clawServo;

void setup() {
    Serial.begin(9600);

    clawServo.attach(3);
    clawServo.write(180);
}

void loop() {
    Serial.println(clawServo.read());
}
