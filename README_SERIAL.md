# Comunicação Serial com o Robô

## Arquivos Principais

- **`robot_serial.py`** - Classe que gerencia comunicação com robô
- **`config_serial.py`** - Configurações de porta, baudrate, calibração
- **`test_serial.py`** - Teste simples de conexão e recebimento de dados

## Uso Básico

### 1. Configurar a Porta Serial

Edite `config_serial.py`:

```python
ROBOT_PORT = "COM3"        # Sua porta (COM3, /dev/ttyUSB0, etc.)
ROBOT_BAUDRATE = 115200    # Sempre 115200
```

### 2. Testar Conexão

```bash
python test_serial.py
```

Deve aparecer algo assim:

```
✓ Conectado ao robô em COM3 (115200 baud)

Recebendo dados do robô (Ctrl+C para parar)...

Frame 1:
  Encoder: L=  1024  R=  1020
  IMU:     ax=   0.12  ay=  -0.05  az=   9.81
  Motores: IL=  200mA  IR=  195mA
  PWM:     L=  50%  R=  50%
  Sensor:  87%
```

## Código para Usar no Simulador

### No main.py:

```python
from robot_serial import RobotSerial
from config_serial import ROBOT_PORT, ROBOT_BAUDRATE

# Criar conexão
robot = RobotSerial(port=ROBOT_PORT, baudrate=ROBOT_BAUDRATE)
robot.connect()

# No loop:
data = robot.read_data()
if data:
    sim.update_robot_data(data)
    sim.update_graphs_from_robot_data()

# Ao terminar:
robot.disconnect()
```

## Protocolo de Comunicação

### Pacote do Microcontrolador (dados):

```
[0xFF] [Length] [Dados] [Checksum]
```

**Estrutura dos dados (17 bytes):**

| Campo | Tipo | Bytes | Escala |
|-------|------|-------|--------|
| encoder_left | int16 | 2 | - |
| encoder_right | int16 | 2 | - |
| imu_ax | int16 | 2 | 0.01 m/s² |
| imu_ay | int16 | 2 | 0.01 m/s² |
| imu_az | int16 | 2 | 0.01 m/s² |
| motor_current_left | int16 | 2 | mA |
| motor_current_right | int16 | 2 | mA |
| pwm_left | int8 | 1 | -100 a 100 |
| pwm_right | int8 | 1 | -100 a 100 |
| sensor_front | uint8 | 1 | 0-100 |

### Pacote do PC (comando):

```
[0xFE] [02] [pwm_left] [pwm_right] [Checksum]
```

## Troubleshooting

### "Cannot open port"

- Verificar se está usando a porta correta
- No Windows: Device Manager → COM/LPT ports
- No Linux: `ls /dev/ttyUSB*`
- Verificar drivers (CH340, CP2102)

### "Checksum error"

- Verificar se microcontrolador envia dados corretos
- Verificar ordem dos bytes (big-endian)

### Sem dados

- Microcontrolador envia dados periodicamente
- Pode levar alguns segundos para os dados chegarem
- Verificar se baudrate bate (115200)

## Próximas Etapas

1. Integrar com `main.py` para receber dados reais
2. Implementar envio de comandos PWM
3. Calcular odometria dos encoders
4. Filtrar dados da IMU
