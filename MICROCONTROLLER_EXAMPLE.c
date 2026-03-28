/*
 * Exemplo de código para MICROCONTROLADOR (STM32, Arduino, etc.)
 * 
 * Este código mostra como enviar dados do robô via serial para o simulador
 * em PC.
 * 
 * Protocolo:
 * [0xFF] [Length] [Data...] [Checksum]
 * 
 * Este é um template - adapte conforme seus sensores e microcontrolador!
 */

#include <stdint.h>
#include <string.h>

// ============================================================================
// CONFIGURAÇÃO
// ============================================================================

#define SERIAL_BAUD 115200
#define TELEM_PERIOD_MS 50  // Enviar dados a cada 50ms (20Hz)

// Pinos de sensores (adapte para seu hardware)
#define ENCODER_LEFT_PIN    A0
#define ENCODER_RIGHT_PIN   A1
#define IMU_SDA_PIN         20  // I2C
#define IMU_SCL_PIN         21  // I2C
#define MOTOR_LEFT_PIN      3
#define MOTOR_RIGHT_PIN     5

// ============================================================================
// ESTRUTURAS DE DADOS
// ============================================================================

typedef struct {
    int16_t encoder_left;           // Contagens
    int16_t encoder_right;          // Contagens
    int16_t imu_ax;                 // 0.01 m/s² por unidade
    int16_t imu_ay;
    int16_t imu_az;
    int16_t motor_current_left;     // mA
    int16_t motor_current_right;
    int8_t  pwm_left;               // -100 a 100
    int8_t  pwm_right;
    uint8_t sensor_front;           // 0-100%
} RobotData;

// ============================================================================
// VARIÁVEIS GLOBAIS
// ============================================================================

RobotData robot_data = {0};
long last_telemetry = 0;

// Contadores de encoder (incrementados por interrupção)
volatile int32_t encoder_left_count = 0;
volatile int32_t encoder_right_count = 0;

// ============================================================================
// FUNÇÕES DE COMUNICAÇÃO SERIAL
// ============================================================================

/**
 * Calcular checksum (XOR de todos os bytes)
 */
uint8_t calculate_checksum(const uint8_t* data, int length) {
    uint8_t checksum = 0;
    for (int i = 0; i < length; i++) {
        checksum ^= data[i];
    }
    return checksum;
}

/**
 * Enviar dados do robô para o simulador
 */
void send_telemetry(void) {
    uint8_t packet[32];
    int idx = 0;
    
    // Header
    packet[idx++] = 0xFF;
    
    // Length (será preenchido depois)
    int length_idx = idx;
    idx++;
    
    // Payload - enviar dados em big-endian (network order)
    
    // Encoder (4 bytes total)
    packet[idx++] = (robot_data.encoder_left >> 8) & 0xFF;
    packet[idx++] = robot_data.encoder_left & 0xFF;
    packet[idx++] = (robot_data.encoder_right >> 8) & 0xFF;
    packet[idx++] = robot_data.encoder_right & 0xFF;
    
    // IMU (6 bytes total)
    packet[idx++] = (robot_data.imu_ax >> 8) & 0xFF;
    packet[idx++] = robot_data.imu_ax & 0xFF;
    packet[idx++] = (robot_data.imu_ay >> 8) & 0xFF;
    packet[idx++] = robot_data.imu_ay & 0xFF;
    packet[idx++] = (robot_data.imu_az >> 8) & 0xFF;
    packet[idx++] = robot_data.imu_az & 0xFF;
    
    // Motor current (4 bytes total)
    packet[idx++] = (robot_data.motor_current_left >> 8) & 0xFF;
    packet[idx++] = robot_data.motor_current_left & 0xFF;
    packet[idx++] = (robot_data.motor_current_right >> 8) & 0xFF;
    packet[idx++] = robot_data.motor_current_right & 0xFF;
    
    // PWM (2 bytes total)
    packet[idx++] = (uint8_t)robot_data.pwm_left;
    packet[idx++] = (uint8_t)robot_data.pwm_right;
    
    // Sensor frontal (1 byte)
    packet[idx++] = robot_data.sensor_front;
    
    // Calculate and store length
    int payload_length = idx - 2;  // Excluir header e length
    packet[length_idx] = payload_length;
    
    // Checksum (calcula sobre header + length + payload)
    uint8_t checksum = calculate_checksum(packet, idx);
    packet[idx++] = checksum;
    
    // Enviar pacote
    for (int i = 0; i < idx; i++) {
        Serial.write(packet[i]);
    }
}

/**
 * Processar comandos recebidos do simulador
 * Formato: [0xFE] [Length] [pwm_left] [pwm_right] [Checksum]
 */
void process_command(void) {
    if (Serial.available() >= 5) {
        uint8_t header = Serial.read();
        
        if (header == 0xFE) {  // Comando (diferente de telemetria)
            uint8_t length = Serial.read();
            
            if (length == 2 && Serial.available() >= 3) {
                int8_t pwm_left = (int8_t)Serial.read();
                int8_t pwm_right = (int8_t)Serial.read();
                uint8_t checksum = Serial.read();
                
                // Verificar checksum
                uint8_t data[4] = {header, length, (uint8_t)pwm_left, (uint8_t)pwm_right};
                if (calculate_checksum(data, 4) == checksum) {
                    // Comando válido - aplicar PWM aos motores
                    apply_motor_control(pwm_left, pwm_right);
                }
            }
        }
    }
}

// ============================================================================
// FUNÇÕES DE SENSORES
// ============================================================================

/**
 * Ler dados dos encoders
 */
void read_encoders(void) {
    robot_data.encoder_left = (int16_t)encoder_left_count;
    robot_data.encoder_right = (int16_t)encoder_right_count;
    
    // Opcionalmente, resetar contadores
    // encoder_left_count = 0;
    // encoder_right_count = 0;
}

/**
 * Ler dados da IMU via I2C
 * Exemplo: MPU6050, BMI160, etc.
 */
void read_imu(void) {
    // Pseudocódigo - adapte para sua IMU
    // float accel_x, accel_y, accel_z;
    // imu.readAccelerometer(&accel_x, &accel_y, &accel_z);
    
    // Converter para 0.01 m/s² por unidade
    // robot_data.imu_ax = (int16_t)(accel_x * 100);
    // robot_data.imu_ay = (int16_t)(accel_y * 100);
    // robot_data.imu_az = (int16_t)(accel_z * 100);
}

/**
 * Ler corrente dos motores via ADC
 */
void read_motor_current(void) {
    // Exemplo: Ler ADC com sensor de corrente
    // A estrutura típica: Sensor -> ADC -> Converter para mA
    
    // Pseudocódigo:
    // int adc_left = analogRead(CURRENT_SENSOR_LEFT);
    // int adc_right = analogRead(CURRENT_SENSOR_RIGHT);
    // robot_data.motor_current_left = adc_left;  // em mA
    // robot_data.motor_current_right = adc_right;
}

/**
 * Ler PWM aplicado (do registro do microcontrolador)
 */
void read_pwm_output(void) {
    // Os valores são definidos quando se aplica motor control
    // Já estão armazenados em robot_data
}

/**
 * Ler sensor frontal (câmera, sensor óptico, etc.)
 */
void read_front_sensor(void) {
    // Exemplo: Sensor óptico/câmera que retorna presença de linha
    // Escala 0-100%
    // int sensor_value = analogRead(SENSOR_FRONT);
    // robot_data.sensor_front = (uint8_t)map(sensor_value, 0, 1023, 0, 100);
}

// ============================================================================
// CONTROLE DE MOTORES
// ============================================================================

/**
 * Aplicar controle PWM aos motores
 */
void apply_motor_control(int8_t pwm_left, int8_t pwm_right) {
    // Limitar valores
    pwm_left = constrain(pwm_left, -100, 100);
    pwm_right = constrain(pwm_right, -100, 100);
    
    // Armazenar para telemetria
    robot_data.pwm_left = pwm_left;
    robot_data.pwm_right = pwm_right;
    
    // Converter percentual para 0-255 PWM
    uint8_t pwm_val_left = (uint8_t)map(abs(pwm_left), 0, 100, 0, 255);
    uint8_t pwm_val_right = (uint8_t)map(abs(pwm_right), 0, 100, 0, 255);
    
    // Definir direção e PWM nos pinos
    if (pwm_left >= 0) {
        digitalWrite(MOTOR_LEFT_PIN + 1, LOW);   // Adelante
    } else {
        digitalWrite(MOTOR_LEFT_PIN + 1, HIGH);  // Atrás
    }
    analogWrite(MOTOR_LEFT_PIN, pwm_val_left);
    
    if (pwm_right >= 0) {
        digitalWrite(MOTOR_RIGHT_PIN + 1, LOW);  // Adelante
    } else {
        digitalWrite(MOTOR_RIGHT_PIN + 1, HIGH); // Atrás
    }
    analogWrite(MOTOR_RIGHT_PIN, pwm_val_right);
}

// ============================================================================
// INTERRUPÇÕES
// ============================================================================

/**
 * Interrupção do encoder esquerdo
 */
void encoder_left_isr(void) {
    encoder_left_count++;
}

/**
 * Interrupção do encoder direito
 */
void encoder_right_isr(void) {
    encoder_right_count++;
}

// ============================================================================
// SETUP
// ============================================================================

void setup(void) {
    // Inicializar serial
    Serial.begin(SERIAL_BAUD);
    
    // Configurar pinos
    pinMode(MOTOR_LEFT_PIN, OUTPUT);
    pinMode(MOTOR_RIGHT_PIN, OUTPUT);
    pinMode(ENCODER_LEFT_PIN, INPUT);
    pinMode(ENCODER_RIGHT_PIN, INPUT);
    
    // Configurar interrupções dos encoders
    attachInterrupt(digitalPinToInterrupt(ENCODER_LEFT_PIN), encoder_left_isr, RISING);
    attachInterrupt(digitalPinToInterrupt(ENCODER_RIGHT_PIN), encoder_right_isr, RISING);
    
    // Inicializar sensores
    // imu.init();
    // sensor.init();
    
    Serial.println("Robot initialized!");
}

// ============================================================================
// LOOP PRINCIPAL
// ============================================================================

void loop(void) {
    // Atualizar sensores
    read_encoders();
    read_imu();
    read_motor_current();
    read_pwm_output();
    read_front_sensor();
    
    // Enviar telemetria periodicamente
    if (millis() - last_telemetry >= TELEM_PERIOD_MS) {
        send_telemetry();
        last_telemetry = millis();
    }
    
    // Processar comandos do simulador
    process_command();
    
    // Pequeno delay para não sobrecarregar
    delayMicroseconds(100);
}

/*
 * NOTAS IMPORTANTES:
 * 
 * 1. Adapte os pinos (ENCODER_LEFT_PIN, etc.) para seu hardware
 * 
 * 2. Calibre os sensores (IMU, corrente, etc.) antes de usar
 * 
 * 3. Certifique-se de que o protocolo serial (baud rate, timings) 
 *    seja compatível com o simulador em PC
 * 
 * 4. Use a mesma ordem de bytes (big-endian) em ambos os lados
 * 
 * 5. Para STM32, STM8, PIC, etc., adapte as funções de I/O:
 *    - Serial.begin() -> HAL_UART_Init() ou similar
 *    - analogRead() -> ADC_Read()
 *    - attachInterrupt() -> uso de handlers de interrupção
 *    - digitalWrite()/analogWrite() -> GPIO ou PWM
 */
