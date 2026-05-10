# ⚡ Dual-Channel Programmable Pulse Generator

A high-precision, non-blocking pulse generator firmware for **STM32 (Blue Pill)** and Arduino-compatible boards. This tool allows for the creation of complex, synchronized signal patterns on two independent channels via UART.

---

## 🛠 Hardware Configuration

| Component | Pin / Detail |
| :--- | :--- |
| **MCU** | STM32F103C8T6 or Arduino |
| **Channel 1 Output** | `PA0` |
| **Channel 2 Output** | `PA1` |
| **Status LED** | `PC13` (Built-in LED) |
| **Baud Rate** | `115200` |

---

## 📡 UART Interface Commands

Connect via Serial Monitor (ensure **Newline (NL)** ending is enabled).

### 1. Manual Control
- `AA`: Toggles **Channel 1** (PA0). Status LED turns ON.
- `BB`: Toggles **Channel 2** (PA1). Status LED turns OFF.

### 2. Pulse Programming (`PULSE:`)
Configure and trigger a sequence for both channels simultaneously.
**Syntax:** `PULSE:1:lvl,dur|lvl,dur&&2:lvl,dur|lvl,dur`

- **lvl**: Logic level (`1` for HIGH, `0` for LOW).
- **dur**: Duration in **microseconds** (µs).
- **|**: Separator between pulse steps.
- **&&**: Separator between Channel 1 and Channel 2.

#### **Example Command:**
`PULSE:1:1,100|0,100|1,200|0,50&&2:1,20|0,100|1,200|0,50`

---

## 📊 Timing Analysis
Based on the example above, the outputs would behave as follows:

### **Channel 1 (PA0)**
1. **High** for 100µs
2. **Low** for 100µs
3. **High** for 200µs
4. **Low** for 50µs (Sequence End)

### **Channel 2 (PA1)**
1. **High** for 20µs
2. **Low** for 100µs
3. **High** for 200µs
4. **Low** for 50µs (Sequence End)

---

## ⚠️ Performance & Usage Notes

* **Non-Blocking:** The code uses `micros()` timing. You can send new commands while a sequence is running without freezing the MCU.
* **Precision:** To maintain microsecond accuracy, **do not** call `Serial.print` or `printDebug()` inside the `loop()` while pulses are active. Serial communication is slow and will cause timing "jitter."
* **Memory Limit:** The current buffer supports up to **64 steps** per channel. This can be increased in the code by adjusting the `Pulse out1[64]` array size.
* **Safe Shutdown:** After a sequence completes, both pins are automatically pulled **LOW** for safety.

---

