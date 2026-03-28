"""
Configuração para comunicação serial com o robô.

Ajuste os valores abaixo conforme seu hardware.
"""

# ============================================================================
# CONFIGURAÇÃO DE PORTA SERIAL
# ============================================================================

# Porta serial do robô
# Windows: "COM1", "COM3", "COM4", etc.
# Linux: "/dev/ttyUSB0", "/dev/ttyACM0", etc.
# macOS: "/dev/tty.usbserial-xxxxx"
ROBOT_PORT = "COM3"

# Velocidade de comunicação (baud rate)
ROBOT_BAUDRATE = 115200

# Timeout de leitura (em segundos)
ROBOT_TIMEOUT = 0.05  # 50ms

# ============================================================================
# CALIBRAÇÃO DO ROBÔ
# ============================================================================

# Raio das rodas (em metros)
WHEEL_RADIUS = 0.02

# Distância entre rodas (em metros)
WHEEL_DISTANCE = 0.15

# Contagens por revolução do encoder
ENCODER_CPR = 512

# ============================================================================
# LIMITES DOS GRÁFICOS
# ============================================================================

GRAPH_LIMITS = {
    "encoder": {"min": -100, "max": 100},
    "imu_accel": {"min": -10, "max": 10},  # m/s²
    "motor_current": {"min": -500, "max": 500},  # mA
    "pwm": {"min": -100, "max": 100},  # %
    "sensor_front": {"min": 0, "max": 100},  # %
    "vel_filtered": {"min": -100, "max": 100},
}
