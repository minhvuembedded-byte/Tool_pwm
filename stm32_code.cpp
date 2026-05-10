#include <Arduino.h>
#include <string.h>

// Cấu trúc lưu trữ từng đoạn xung
struct Pulse {
  int level;
  uint32_t duration; // Microseconds
};

// Định nghĩa chân cắm
const int pin1 = PA0;
const int pin2 = PA1;
const int ledPin = PC13; // LED trạng thái trên board STM32

// Bộ nhớ đệm cho xung (tối đa 64 bước mỗi kênh)
Pulse out1[64], out2[64];
int len1 = 0, len2 = 0;

// Biến điều khiển luồng
int idx1 = 0, idx2 = 0;
uint32_t prevMicros1 = 0, prevMicros2 = 0;
bool running1 = false, running2 = false;

// --- HÀM XỬ LÝ DỮ LIỆU TỪNG KÊNH ---
void parseChannelData(int channel, char* data) {
  int count = 0;
  char* savePtr;
  
  // Tách từng cặp pulse bằng dấu '|'
  char* pulsePtr = strtok_r(data, "|", &savePtr);
  
  while (pulsePtr != NULL && count < 64) {
    char* commaPtr = strchr(pulsePtr, ',');
    if (commaPtr != NULL) {
      *commaPtr = '\0'; // Tách mức logic và thời gian
      
      int lvl = atoi(pulsePtr);
      uint32_t dur = (uint32_t)strtoul(commaPtr + 1, NULL, 10);
      
      if (channel == 1) {
        out1[count].level = lvl;
        out1[count].duration = dur;
      } else {
        out2[count].level = lvl;
        out2[count].duration = dur;
      }
      count++;
    }
    pulsePtr = strtok_r(NULL, "|", &savePtr);
  }
  
  if (channel == 1) len1 = count;
  else if (channel == 2) len2 = count;
}

// --- HÀM PHÂN TÁCH CHUỖI TỔNG ---
void parsePulseCommand(char* str) {
  // Tìm vị trí tách 2 kênh bằng "&&"
  char* separator = strstr(str, "&&");
  if (separator == NULL) return;

  *separator = '\0';           // Cắt chuỗi làm 2 phần tại "&&"
  char* part1 = str;           // "PULSE:1:..."
  char* part2 = separator + 2; // "2:..."

  // Tìm dữ liệu kênh 1 (sau dấu ':' thứ hai)
  char* c1Start = strchr(part1, ':');
  if (c1Start) {
    c1Start = strchr(c1Start + 1, ':');
    if (c1Start) parseChannelData(1, c1Start + 1);
  }

  // Tìm dữ liệu kênh 2 (sau dấu ':' đầu tiên của phần 2)
  char* c2Start = strchr(part2, ':');
  if (c2Start) {
    parseChannelData(2, c2Start + 1);
  }
}

// --- KÍCH HOẠT BẮN XUNG ĐỒNG BỘ ---
void startSequence() {
  uint32_t now = micros();
  
  if (len1 > 0) {
    idx1 = 0;
    prevMicros1 = now;
    digitalWrite(pin1, out1[0].level);
    running1 = true;
  }
  
  if (len2 > 0) {
    idx2 = 0;
    prevMicros2 = now;
    digitalWrite(pin2, out2[0].level);
    running2 = true;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(pin1, OUTPUT);
  pinMode(pin2, OUTPUT);
  pinMode(ledPin, OUTPUT);
  
  digitalWrite(pin1, LOW);
  digitalWrite(pin2, LOW);
  digitalWrite(ledPin, HIGH); // Tắt LED (tùy board)
  
  Serial.println("--- STM32 Pulse Generator Ready ---");
}

void loop() {
  // 1. ĐỌC UART VÀ XỬ LÝ LỆNH
  if (Serial.available() > 0) {
    static char buffer[512];
    static int pos = 0;
    
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (pos > 0) {
        buffer[pos] = '\0';
        
        if (strcmp(buffer, "AA") == 0) {
          digitalWrite(ledPin, LOW); // Bật LED
          digitalWrite(pin1, !digitalRead(pin1));
          Serial.println("Toggle Pin 1");
        }
        else if (strcmp(buffer, "BB") == 0) {
          digitalWrite(ledPin, HIGH); // Tắt LED
          digitalWrite(pin2, !digitalRead(pin2));
          Serial.println("Toggle Pin 2");
        }
        else if (strncmp(buffer, "PULSE:", 6) == 0) {
          // Dừng mọi xung đang chạy để nạp mới
          running1 = false;
          running2 = false;
          
          parsePulseCommand(buffer);
          
          if (len1 > 0 || len2 > 0) {
            startSequence();
            Serial.println("Pulse Configured & Started!");
          }
        }
        pos = 0; // Reset buffer
      }
    } else if (pos < 511) {
      buffer[pos++] = c;
    }
  }

  // 2. LOGIC PHÁT XUNG KÊNH 1
  uint32_t now = micros();
  if (running1) {
    if (now - prevMicros1 >= out1[idx1].duration) {
      idx1++;
      if (idx1 < len1) {
        digitalWrite(pin1, out1[idx1].level);
        prevMicros1 = now;
      } else {
        digitalWrite(pin1, LOW); // Kết thúc chuỗi
        running1 = false;
      }
    }
  }

  // 3. LOGIC PHÁT XUNG KÊNH 2
  if (running2) {
    if (now - prevMicros2 >= out2[idx2].duration) {
      idx2++;
      if (idx2 < len2) {
        digitalWrite(pin2, out2[idx2].level);
        prevMicros2 = now;
      } else {
        digitalWrite(pin2, LOW); // Kết thúc chuỗi
        running2 = false;
      }
    }
  }
}