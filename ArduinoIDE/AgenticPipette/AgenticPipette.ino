#include <Arduino.h>
#include <Servo.h>
#include <stdlib.h>
#include <string.h>

const uint8_t SERVO_PIN=9, ENA=5, IN1=4, IN2=8;
const unsigned long MAX_MOVE_MS=10000, LINK_TIMEOUT_MS=2000;
Servo servo;
char line[96];
uint8_t used=0;
bool overflow=false, active=false, motorOn=false;
unsigned long activeId=0, started=0, duration=0, lastContact=0;
int angle=-1;

void event(unsigned long id, const char* type, const char* detail) {
  Serial.print(F("{\"id\":")); Serial.print(id);
  Serial.print(F(",\"event\":\"")); Serial.print(type);
  Serial.print(F("\",\"detail\":\"")); Serial.print(detail); Serial.println(F("\"}"));
}
void motorOff() {
  digitalWrite(ENA,LOW); digitalWrite(IN1,LOW); digitalWrite(IN2,LOW); motorOn=false;
}
void outputsOff() { motorOff(); servo.detach(); digitalWrite(SERVO_PIN,LOW); }
void cancel(const char* reason) {
  outputsOff();
  if(active) event(activeId,"error",reason);
  active=false;
}
bool number(const char* s,long low,long high,long& out) {
  if(!s || !*s) return false;
  char* end; out=strtol(s,&end,10);
  return end!=s && !*end && out>=low && out<=high;
}
void status(unsigned long id) {
  Serial.print(F("{\"id\":")); Serial.print(id);
  Serial.print(F(",\"event\":\"status\",\"protocol\":1,\"busy\":")); Serial.print(active?F("true"):F("false"));
  Serial.print(F(",\"actuator_on\":")); Serial.print(motorOn?F("true"):F("false"));
  Serial.print(F(",\"servo_attached\":")); Serial.print(servo.attached()?F("true"):F("false"));
  Serial.print(F(",\"commanded_angle\":")); Serial.print(angle);
  Serial.println(F(",\"position_feedback\":false}"));
}
void service() {
  if(active && activeId && millis()-lastContact>=LINK_TIMEOUT_MS) { cancel("heartbeat_timeout"); return; }
  if(active && millis()-started>=duration) {
    motorOff(); active=false; event(activeId,"done","timer_elapsed_not_position_verified");
  }
}
void command(char* text) {
  char* t[7]; uint8_t n=0;
  char* item=strtok(text," \t");
  while(item && n<7) {t[n++]=item; item=strtok(NULL," \t");}
  if(!n) return;
  unsigned long id=0; uint8_t k=0; long v=0;
  if(t[0][0]=='@') {
    if(!number(t[0]+1,1,2147483647L,v)) {event(0,"error","invalid_id"); return;}
    id=v; k=1;
  }
  if(k>=n || item || n==7) {event(id,"error","invalid_command"); return;}
  const char* op=t[k]; uint8_t args=n-k-1;
  if(!strcmp(op,"stop") && !args) {
    cancel("stopped"); event(id,"done","outputs_disabled"); return;
  }
  if(!strcmp(op,"ping") && !args) {lastContact=millis(); event(id,"pong","alive"); return;}
  if(!strcmp(op,"status") && !args) {status(id); return;}
  if(!strcmp(op,"help") && !args) {
    event(id,"help","servo ANGLE SETTLE_MS | actuator forward/reverse MS | wait MS | stop | status | ping; prefix @ID for agents"); return;
  }
  if(active) {event(id,"error","busy"); return;}
  long ms=0, deg=0, pulse=0;
  bool rawServo=false;
  bool moveServo=false, moveMotor=false, reverse=false;
  if(!strcmp(op,"servo") && args==2 && number(t[k+1],0,180,deg) && number(t[k+2],1,MAX_MOVE_MS,ms)) moveServo=true;
  else if(!strcmp(op,"servo_us") && args==2 && number(t[k+1],610,2000,pulse) && number(t[k+2],1,5000,ms)) rawServo=true;
  else if(!strcmp(op,"actuator") && args==2 && number(t[k+2],1,MAX_MOVE_MS,ms) &&
          (!strcmp(t[k+1],"forward") || !strcmp(t[k+1],"reverse"))) {
    moveMotor=true; reverse=!strcmp(t[k+1],"reverse");
  } else if(!strcmp(op,"wait") && args==1 && number(t[k+1],1,60000,ms)) {}
  // Serial Monitor shortcuts remain available; angles are absolute.
  else if(!id && !args && number(op,0,180,deg)) {moveServo=true; ms=500;}
  else if(!id && !args && (!strcmp(op,"actuator") || !strcmp(op,"forward") || !strcmp(op,"reverse"))) {
    moveMotor=true; reverse=!strcmp(op,"reverse"); ms=5000;
  } else {event(id,"error","invalid_arguments"); return;}
  motorOff();
  if(moveServo) {
    angle=deg; servo.writeMicroseconds(1000+(deg*1000L+90)/180);
    if(!servo.attached()) servo.attach(SERVO_PIN,610,2000);
  }
  if(rawServo) {
    angle=-1; // Raw pulse is not a calibrated angle.
    servo.writeMicroseconds(pulse);
    if(!servo.attached()) servo.attach(SERVO_PIN,610,2000);
  }
  if(moveMotor) {
    digitalWrite(IN1,reverse?LOW:HIGH); digitalWrite(IN2,reverse?HIGH:LOW);
    digitalWrite(ENA,HIGH); motorOn=true;
  }
  activeId=id; duration=ms; started=millis(); lastContact=started; active=true;
  event(id,"ack","started");
}
void setup() {
  digitalWrite(ENA,LOW); digitalWrite(IN1,LOW); digitalWrite(IN2,LOW);
  pinMode(ENA,OUTPUT); pinMode(IN1,OUTPUT); pinMode(IN2,OUTPUT);
  pinMode(SERVO_PIN,OUTPUT); outputsOff(); Serial.begin(115200);
  event(0,"ready","agentic_pipette_protocol_1");
}
void loop() {
  service();
  for(uint8_t count=0; count<16 && Serial.available(); ++count) {
    char c=(char)Serial.read();
    if(c=='\r' || c=='\n') {
      if(overflow) event(0,"error","line_too_long");
      else {line[used]=0; command(line);}
      used=0; overflow=false;
    } else if(!overflow) {
      if(used<sizeof(line)-1) line[used++]=c; else overflow=true;
    }
    service();
  }
}
