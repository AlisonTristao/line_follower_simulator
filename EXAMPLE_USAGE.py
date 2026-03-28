"""
Exemplo: Como integrar robot_serial.py com o simulador.

Este arquivo mostra os passos necessários.
"""

# ============================================================================
# PASSO 1: Importar módulo
# ============================================================================

from robot_serial import RobotSerial
from config_serial import ROBOT_PORT, ROBOT_BAUDRATE


# ============================================================================
# PASSO 2: Conectar ao robô
# ============================================================================

robot = RobotSerial(port=ROBOT_PORT, baudrate=ROBOT_BAUDRATE)

if not robot.connect():
    print("Erro ao conectar!")
    exit(1)


# ============================================================================
# PASSO 3: Ler dados no loop
# ============================================================================

while True:
    # Tenta ler pacote de dados
    data = robot.read_data()
    
    if data:
        # Dados recebidos com sucesso
        print(f"Encoder L: {data['encoder_left']}")
        print(f"Encoder R: {data['encoder_right']}")
        print(f"PWM L: {data['pwm_left']}")
        # ... etc
    else:
        # Sem dados ainda
        print("Aguardando dados...")


# ============================================================================
# PASSO 4: Enviar comandos (opcional)
# ============================================================================

# robot.send_command(pwm_left=50, pwm_right=50)


# ============================================================================
# PASSO 5: Desconectar
# ============================================================================

robot.disconnect()


# ============================================================================
# INTEGRAÇÃO COMPLETA COM SIMULADOR
# ============================================================================

"""
No main_serial.py, a integração é feita assim:

1. Criar instância:
   robot = RobotSerial(port=ROBOT_PORT, baudrate=ROBOT_BAUDRATE)
   robot.connect()

2. No loop principal:
   robot_data = robot.read_data()
   if robot_data:
       sim.update_robot_data(robot_data)
       sim.update_graphs_from_robot_data()

3. Ao terminar:
   robot.disconnect()

Veja main_serial.py para exemplo completo.
"""
