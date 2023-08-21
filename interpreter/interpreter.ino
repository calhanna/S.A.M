// This code just interprets instructions from the GUI and drives the motors according to them. All the heavy lifting gets done at Python level.

#include <Servo.h>

const byte numChars = 32;       // 32 character limit, shouldn't be a problem. Will refine down later.
char receivedChars[numChars];   // Serial data is stored as an char array

boolean newData = false;  // When we finish reading a string of instructions, this variable gets set to true

// These variables are related to the serial reading.
static byte ndx = 0;  // Number of recieved characters
char endMarker = 'n'; // This character goes at the end of an instruction string
char hardEndMarker = 'N'; // Used for scripting 
char rc;              // Currently recieved character

const float phase_angle = 0.9; // All stepper motors in this design have an angle of 1.8 degrees between steps.

int current_ms;
int prev_ms;
int dt;

bool notifyAtEnd;

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
    int DIR; 
    int ms_del; // The amount of time in ms to wait between steps
    int multiplier;
    StepperOperation current_op;
    void new_op(int goal_steps, int dir);
    void clear_op();
    void drive_motor();
    uint8_t limit_pin;
};

void StepperMotor::new_op(int goal_steps, int dir) {
  current_op.steps = 0;
  current_op.max_steps = goal_steps * multiplier;
  current_op.DIR = dir; // HIGH = 1 = forward, LOW = 0 = backward
}

void StepperMotor::clear_op() {
  current_op.steps = 0;
  current_op.max_steps = 0;
  if (notifyAtEnd) {
    Serial.write('0');
    notifyAtEnd = false;
  }
}

void StepperMotor::drive_motor() {
  // Usually you'd do this by delaying a certain amount of microseconds. 
  // However, I want my motors to move in sync.
  // Thus, instead of using an actual delay, we loop through over and over again, calculating the elapsed time each loop, and use this to run the motor for the required amount of time
  // This does result in some very slight inaccuracy, but it should be fine I ~~hope~~ think.
  
  //if ((digitalRead(limit_pin) == 0 and current_op.DIR == 1 ) == false) {  // Check limit switch
    if (current_op.steps <= current_op.max_steps) {                       // Check for operation completion
      if (current_op.current_del <= dt * 2) {                             // Start step. We multiply this by 2 because we add to the current_del at the end of every loop no matter what. It's clumsy, but faster than altering the code to stop doing that.
        digitalWrite(DIR, current_op.DIR);   // Set Direction
        digitalWrite(PUL,HIGH);             // Send pulse
      } else if (current_op.current_del > ms_del - 50 && current_op.current_del < ms_del + 50) {  // Wait ms_del microseconds. Average dt is between 18 and 30us, so we have a safety range here so we never skip a step (hopefully)
        digitalWrite(PUL,LOW);              // Finish pulse
      } else if (current_op.current_del > (ms_del * 2) - 50 && current_op.current_del < (ms_del * 2) + 50) { // Wait another ms_del microseconds
        // Reset in preperation for next pulse
        current_op.current_del = 0;
        current_op.steps ++; 
      }
      current_op.current_del += dt;
    } else if (current_op.max_steps != 0) {
      clear_op();
    } 
  //} else {
  //  clear_op();
  //}
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

    if (rc != endMarker && rc != hardEndMarker) {
      receivedChars[ndx] = rc;        
      ndx++;
      if (ndx >= numChars) {
        ndx = numChars - 1;
      }
    }
    else {
      receivedChars[ndx] = 'N';
      receivedChars[ndx + 1] = '\0';      // Terminate the string
      ndx = 0;
      newData = true;                 // NEW DATA
    }
  }
}

int interpret(String input_str) {
  // Takes the output string from the GUI program and interprets it as instructions
  // Then, creates a new StepperOperation and assigns it to the relevant StepperMotor

  if (input_str[input_str.length()-1] == 'N') {
    input_str = input_str.substring(0, input_str.length()-2);
    notifyAtEnd = true;
  }

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
    shoulder1.new_op(steps, DIR);  
    shoulder2.new_op(steps, DIR);    
  } else if (identifier == 'e') { // Elbow
    elbow.new_op(steps, DIR); 
  } else if (identifier == 'b') {
    base.new_op(steps, DIR);
  } else if (identifier == 'w') { // Big wrist servo
    wrist1.write(angle);
  } else if (identifier == 'r') { // Small wrist servo
    wrist2.write(angle);
  } else if (identifier == 'g') {
    claw.write(180);
  }
  return 1;
}

void setup() {
  // put your setup code here, to run once:

  Serial.begin(9600); // 9600 baud is the baudrate of the rfcomm0 port on my laptop. Also works for standard usb connections so we vibing.

  // Define pins 3 to 13 as output
  for (int i = 3; i <= 13; i++) {
    pinMode(i, OUTPUT);
  } 

  // Initialise stepper motors

  // Left shoulder stepper, 34mm
  shoulder1.PUL = 13;
  shoulder1.DIR = 12;
  shoulder1.ms_del = 10000;
  shoulder1.multiplier = 8;
  shoulder1.limit_pin = A0;
  pinMode(A0, INPUT_PULLUP);

  // Right shoulder stepper, 34mm 
  shoulder2.PUL = 11;
  shoulder2.DIR = 10;
  shoulder2.ms_del = 10000;
  shoulder2.multiplier = 8;
  shoulder2.limit_pin = A0;
  
  // Base rotating stepper, 40mm
  base.PUL = 9;
  base.DIR = 8;
  base.ms_del = 5000;
  base.multiplier = 20;
  base.limit_pin = A2;
  
  // Pancake stepper in the elbow, 24mm
  elbow.PUL = 7;
  elbow.DIR = 6;
  elbow.ms_del = 5000;
  elbow.multiplier = 6;
  elbow.limit_pin = A1;
  pinMode(A1, INPUT_PULLUP);

  // Initialise servos
  wrist1.attach(5);
  wrist1.write(90);
  wrist2.attach(4);
  claw.attach(3);
}

void loop() {
  // Calculate time interval between loops
  prev_ms = current_ms;
  current_ms = micros();
  dt = current_ms - prev_ms;

  read(); // Read serial data from gui.
  if (newData==true) {
    Serial.println(receivedChars);
    interpret(receivedChars);
    newData = false;
  }

  //Serial.println(digitalRead(A0));

  shoulder1.drive_motor();
  shoulder2.drive_motor();
  elbow.drive_motor();
  base.drive_motor();
}
