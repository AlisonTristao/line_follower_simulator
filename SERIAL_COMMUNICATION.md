# Sistema de Comunicação Serial com Robô Real

## Visão Geral

O simulador foi refatorado para receber dados de um robô real via comunicação serial com um microcontrolador. O sistema agora exibe gráficos em tempo real dos seguintes dados:

### Dados Recebidos do Robô

1. **Encoder** (velocidade)
   - Encoder esquerdo (RPM ou contagens)
   - Encoder direito (RPM ou contagens)

2. **IMU** (Aceleração)
   - Aceleração em X (ax)
   - Aceleração em Y (ay)
   - Aceleração em Z (az)

3. **Motores**
   - Corrente motor esquerdo (mA)
   - Corrente motor direito (mA)

4. **Controle**
   - PWM aplicado esquerdo (-100% a +100%)
   - PWM aplicado direito (-100% a +100%)

5. **Sensores**
   - Leitura do sensor frontal (0% a 100%)

6. **Velocidade Filtrada** (para implementar filtro depois)
   - Velocidade média (vm)
   - Velocidade angular (ω)

## Configuração de Limites dos Gráficos

Os limites mín/máx dos gráficos são definidos em `simulator.py` na variável `GRAPH_LIMITS`:

```python
GRAPH_LIMITS = {
    "encoder": {"min": -100, "max": 100},
    "imu_accel": {"min": -100, "max": 100},
    "motor_current": {"min": -100, "max": 100},
    "pwm": {"min": -100, "max": 100},
    "sensor_front": {"min": 0, "max": 100},
    "vel_filtered": {"min": -100, "max": 100},
}
```

**Valores padrão:** -100% a +100% para a maioria dos dados, 0% a 100% para sensor frontal.

## Usando o Simulador

### Modo Simulado (Sem Robô Conectado)

```bash
python main.py
```

Neste modo, o simulador gera dados aleatórios para visualizar os gráficos.

### Modo com Robô Real (Serial)

```bash
python main_with_serial.py
```

Configure o arquivo `main_with_serial.py`:

```python
ROBOT_SERIAL_PORT = "COM3"  # Altere para a porta do seu robô
USE_SERIAL_COMMUNICATION = True  # Mude para True quando conectar o robô
```

## Módulo de Comunicação Serial

### Arquivo: `serial_communication.py`

Classe principal: `RobotSerialCommunication`

#### Inicialização

```python
from serial_communication import RobotSerialCommunication

robot = RobotSerialCommunication(
    port="COM3",        # Porta serial
    baudrate=115200,    # Velocidade de comunicação
    timeout=0.1         # Timeout de leitura em segundos
)
```

#### Conectar/Desconectar

```python
if robot.connect():
    # Comunicação estabelecida
    pass
else:
    # Falha na conexão
    pass

robot.disconnect()
```

#### Receber Dados

```python
result = robot.receive_data()

if result:
    sensor_data, delta_x, delta_y = result
    print(f"Encoder esquerdo: {sensor_data['encoder_left']}")
    print(f"Posição: ({delta_x}, {delta_y})")
```

#### Enviar Comandos

```python
# Enviar velocidade para os motores
robot.send_command(pwm_left=50, pwm_right=50)
```

### Protocolo de Comunicação

#### Formato do Pacote de Dados (do Microcontrolador)

```
[Header] [Length] [Data...] [Checksum]
  0xFF     N       N bytes    1 byte (XOR)
```

#### Estrutura do Payload (20+ bytes)

| Campo | Tipo | Bytes | Descrição |
|-------|------|-------|-----------|
| encoder_left | int16 | 2 | Contagens do encoder esquerdo |
| encoder_right | int16 | 2 | Contagens do encoder direito |
| imu_ax | int16 | 2 | Aceleração X em 0.01 m/s² |
| imu_ay | int16 | 2 | Aceleração Y em 0.01 m/s² |
| imu_az | int16 | 2 | Aceleração Z em 0.01 m/s² |
| motor_current_left | int16 | 2 | Corrente esquerda em mA |
| motor_current_right | int16 | 2 | Corrente direita em mA |
| pwm_left | int8 | 1 | PWM esquerdo (-100 a 100) |
| pwm_right | int8 | 1 | PWM direito (-100 a 100) |
| sensor_front | uint8 | 1 | Sensor frontal (0 a 100) |

**Total: ~20 bytes**

### Odometria

O módulo calcula automaticamente `delta_x` e `delta_y` baseado nos encoders:

```python
# Parâmetros calibráveis
robot.WHEEL_RADIUS = 0.02       # metros
robot.WHEEL_DISTANCE = 0.15     # metros entre rodas
robot.ENCODER_CPR = 512         # contagens por revolução
```

## Integração com Simulador

### Atualizar Dados do Robô

```python
# No main.py ou main_with_serial.py
result = robot.receive_data()

if result:
    sensor_data, delta_x, delta_y = result
    
    # Atualizar simulador com dados reais
    sim.update_robot_data(sensor_data)
    sim.update_graphs_from_robot_data()
    
    # Mover robô na visualização
    data = sim.step(delta_x, delta_y)
```

### Posição do Robô

A posição do robô na visualização é atualizada por:

1. **Delta X, Y**: Recebidos do cálculo de odometria dos encoders
2. **Track Movement**: O track é movido pela quantidade de deslocamento do robô

## Customização

### Adicionar Novos Gráficos

1. Adicione em `GRAPH_LIMITS` em `simulator.py`
2. Adicione no setup em `_setup_display_graphs()`
3. Adicione em `update_graphs_from_robot_data()`
4. Adicione o campo no dicionário `robot_data` em `_init_simulation_objects()`

### Mudar Limites dos Gráficos

Edite `GRAPH_LIMITS` em `simulator.py`:

```python
GRAPH_LIMITS = {
    "encoder": {"min": -500, "max": 500},  # Novos limites
}
```

### Calibrar Odometria

Antes de usar, calibre os parâmetros do robô:

```python
robot.WHEEL_RADIUS = 0.02        # Meça o raio da roda
robot.WHEEL_DISTANCE = 0.15      # Meça a distância entre rodas
robot.ENCODER_CPR = 512          # Verifique na documentação do encoder
```

## Estrutura de Arquivos

```
line_follower_simulator/
├── main.py                      # Simulação com dados aleatórios
├── main_with_serial.py          # Simulação com dados reais do robô
├── serial_communication.py       # Módulo de comunicação serial
├── simulator.py                 # Simulador (refatorado para dados reais)
├── settings.py                  # Configuração
├── graphics/
│   ├── graphics_elements.py     # Sistema de gráficos
│   └── track_generator.py       # Gerador de track
├── car_modeling/                # (Removido - sistema de simulação de dinâmica)
└── imagens/                     # Recursos visuais
```

## Próximas Etapas

1. **Implementar Filtro para Velocidade Filtrada**
   - Implementar Filtro de Kalman ou média móvel
   - Método no módulo ou na classe GameSimulation

2. **Enviar Comandos de Motor**
   - Implementar loop de controle PID
   - Enviar PWM via `robot.send_command()`

3. **Calibração Automática**
   - Função de calibração interativa
   - Ajustar parâmetros dinamicamente

4. **Log de Dados**
   - Salvar dados do robô em arquivo para análise

5. **Processamento do Sensor Frontal**
   - Implementar detecção de linha baseada no sensor
   - Calcular erro de posição

## Teste Rápido

```bash
# 1. Conectar robô via USB
# 2. Identificar a porta serial (COM3, /dev/ttyUSB0, etc.)
# 3. Editar main_with_serial.py com a porta correcta
# 4. Rodar:
python main_with_serial.py
```

A visualização deve mostrar os gráficos atualizando com dados do robô em tempo real!

## Troubleshooting

### "Could not connect to robot"
- Verificar se o microcontrolador está conectado
- Verificar a porta serial correta
- Verificar o baudrate (padrão 115200)
- Verificar drivers USB (CH340, CP2102, etc.)

### "Checksum error"
- Verificar o protocolo de comunicação do microcontrolador
- Verificar se o cálculo de checksum está correto

### Gráficos não atualizam
- Verificar se `update_graphs_from_robot_data()` está sendo chamado
- Verificar se `update_robot_data()` recebe dados válidos

## Contato/Suporte

Para questões sobre o protocolo de comunicação, referir-se ao código-fonte em `serial_communication.py`.
