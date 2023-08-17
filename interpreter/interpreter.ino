// This code just interprets instructions from the GUI and drives the motors according to them. All the heavy lifting gets done at Python level.

/*
Current challenge is timing. Given how we control stepper motors in sync, the time elapsed for each loop is extremely important
Largest time losses are reading analog ports and sending data over serial
digitalRead() cuts reading time from >100us (using analogRead) to <5us, which is excellent
Serial data sendtimes depend on the baudrate. 9600 is the limit for bluetooth, which is far too slow. Will likely disable all feedback from the arduino over bluetooth.
The greater the elapsed time the less accurate the results will be as it increases the error in the pulse timings.
Ideally we want it to be as low as 50ms
We don't need to send serial data on every loop, so we can cut down on that. Will result in small hiccups if we send data in motion.
Serial reading is also slow, but we do it very rarely and almost never in motion.
*/

#include <Servo.h>

const byte numChars = 32;       // 32 character limit, shouldn't be a problem. Will refine down later.
char receivedChars[numChars];   // Serial data is stored as an char array

boolean newData = false;  // When we finish reading a string of instructions, this variable gets set to true

// These variables are related to the serial reading.
static byte ndx = 0;  // Number of recieved characters
char endMarker = 'n'; // This character goes at the end of an instruction string
char rc;              // Currently recieved character

const float phase_angle = 0.9; // All stepper motors in this design have an angle of 1.8 degrees between steps.

int current_ms;
int prev_ms;
int dt;

// We want different parts of the robot to move at the same time. Thus, we keep track of each operation using one of these objects, which keeps track of how many steps it's motor has to move
class StepperOperation {
  public: 
    int max_steps;
    int steps;
    int DIR;
    int current_del;
};

class StepperMotor {
  public: 
    int PUL;  // Set this to high to make the motor move
    int DIR;  // HIGH = 1 = forward, LOW = 0 = backward
    int ms_del; // The amount of time in ms to wait between steps
    float ratio;
    StepperOperation current_op;
    void drive_motor();
};

void StepperMotor::drive_motor() {
  // Usually you'd do this by delaying a certain amount of microseconds. 
  // However, I want my motors to move in sync.
  // Thus, instead of using an actual delay, we loop through over and over again, calculating the elapsed time each loop, and use this to run the motor for the required amount of time
  // This does result in some very slight inaccuracy, but it should be fine I ~~hope~~ think.

  if (current_op.steps <= current_op.max_steps) {
    if (current_op.current_del <= dt * 2) {
      digitalWrite(DIR, current_op.DIR);   // Set Direction
      digitalWrite(PUL,HIGH);             // Activate motor
    } else if (current_op.current_del > ms_del - 500 && current_op.current_del < ms_del + 500) {  // Wait ms_del microseconds. Average dt is between 18 and 30us, so we have a safety range here so we never skip a step (hopefully)
      digitalWrite(PUL,LOW);              // Stop motor
    } else if (current_op.current_del > (ms_del * 2) - 500 && current_op.current_del < (ms_del * 2) + 500) { // Wait another ms_del microseconds
      current_op.current_del = 0;
      current_op.steps ++; 
    }
    current_op.current_del += dt;
  }
}

// Declare Stepper Motors
StepperMotor shoulder1;
StepperMotor shoulder2;
StepperMotor elbow;
StepperMotor base;

// Declare servos
Servo wrist1;   // Big servo in the wrist
Servo wrist2;   // Smaller servo in the wrist
Servo claw;     // Micro servo controlling the claw

void read() {
  // This function reads a whole string of serial input rather than single characters. Adapted from stackoverflow.
  if (Serial.available() > 0 && newData == false) {
    rc = Serial.read();               // Fetch latest character

    if (rc != endMarker) {
      receivedChars[ndx] = rc;        
      ndx++;
      if (ndx >= numChars) {
        ndx = numChars - 1;
      }
    }
    else {
      receivedChars[ndx] = '\0';      // Terminate the string
      ndx = 0;
      newData = true;                 // NEW DATA
    }
  }
}

int interpret(String input_str) {
  // Takes the output string from the GUI program and interprets it as instructions
  // Then, creates a new StepperOperation and assigns it to the relevant StepperMotor
  char identifier = input_str[0]; // Single character at the start of the instructions that indicates the motor / pair of motors / stepper to drive

  // Isolate the angle, the second segment, from the instructions by looping through until we find an _
  char c;
  String n;
  for (int i = 2; i < sizeof(input_str); i++) {
    c = input_str[i];
    if (c != '_') {
      n += c;
    } else {
      break;
    }
  } 

  int angle = n.toInt();
  int steps = (angle / phase_angle)/2;  // Calculate the necessary steps to achieve the necessary angle.
  int DIR = input_str.substring(input_str.length()-2, input_str.length()-1).toInt(); // Second to last segment of the instructions indicates the direction

  if (identifier == 's') {        // Shoulder
    // Reset the current_op of the relevant motors
    shoulder1.current_op.steps = 0;
    shoulder2.current_op.steps = 0;

    shoulder1.current_op.max_steps = steps * 8;
    shoulder2.current_op.max_steps = steps * 8;

    shoulder1.current_op.DIR = DIR;
    shoulder2.current_op.DIR = DIR;      
  } else if (identifier == 'e') { // Elbow
    elbow.current_op.steps = 0;

    elbow.current_op.max_steps = steps * 5;

    elbow.current_op.DIR = DIR;
  } else if (identifier == 'b') {
    base.current_op.steps = 0;

    base.current_op.max_steps = steps * 5;

    base.current_op.DIR = DIR;
  } else if (identifier == 'w') { // Big wrist servo
    wrist1.write(angle);
  } else if (identifier == 'r') { // Small wrist servo
    wrist2.write(angle);
  }
  return 1;
}

void setup() {
  // put your setup code here, to run once:

  // Baudrates:
  //  9600 - default. 6400ms to send data. bluetooth supported
  //  57600 - 800ms to send data
  //  115200 - 400ms to send data
  // We want less than 50ms so sending data is probably impossible
  Serial.begin(9600); 

  // Define pins 3 to 13 as output
  for (int i = 3; i <= 13; i++) {
    pinMode(i, OUTPUT);
  } 

  pinMode(A0, INPUT_PULLUP);
  pinMode(A1, INPUT_PULLUP);
  pinMode(A2, INPUT_PULLUP);
  pinMode(A3, INPUT_PULLUP);
  pinMode(A4, INPUT_PULLUP);
  pinMode(A5, INPUT_PULLUP);

  // Initialise stepper motors

  // Left shoulder stepper, 34mm
  shoulder1.PUL = 13;
  shoulder1.DIR = 12;
  shoulder1.ms_del = 10000;
  shoulder1.ratio = 16/120; // 1:7.5

  // Right shoulder stepper, 34mm 
  shoulder2.PUL = 11;
  shoulder2.DIR = 10;
  shoulder2.ms_del = 10000;
  shoulder1.ratio = 16/120;
  
  // Base rotating stepper, 40mm
  base.PUL = 9;
  base.DIR = 8;
  base.ms_del = 5000;
  base.ratio = 1/20;
  
  // Pancake stepper in the elbow, 24mm
  elbow.PUL = 7;
  elbow.DIR = 6;
  elbow.ms_del = 5000;
  elbow.ratio = 16/88; // 1: 5.5

  // Initialise servos
  wrist1.attach(5);
  wrist2.attach(4);
  claw.attach(3);
}

int n;
void loop() {
  // Calculate time interval between loops
  prev_ms = current_ms;
  current_ms = micros();
  dt = current_ms - prev_ms;

  read(); // Read serial data from gui.
  if (newData) {
    interpret(receivedChars);
    newData = false;
  }

  if (digitalRead(A0) == 0 && shoulder1.current_op.DIR == 1) {
    shoulder1.current_op.steps = 0;
    shoulder1.current_op.max_steps = 0;
    shoulder1.current_op.current_del = 0;
    shoulder2.current_op.steps = 0;
    shoulder2.current_op.max_steps = 0;
    shoulder2.current_op.current_del = 0;
  }
  if (digitalRead(A1) == 0 && elbow.current_op.DIR == 1) {
    shoulder1.current_op.steps = 0;
    shoulder1.current_op.max_steps = 0;
    shoulder1.current_op.current_del = 0;
  }

  shoulder1.drive_motor();
  shoulder2.drive_motor();
  elbow.drive_motor();
  base.drive_motor();
}