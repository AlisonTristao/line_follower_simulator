"""
Teste simples de comunicação serial.

Conecta ao robô e imprime os dados recebidos.
"""

from robot_serial import RobotSerial
from config_serial import ROBOT_PORT, ROBOT_BAUDRATE
import time


def main():
    """Função principal de teste."""
    
    # Cria instância de comunicação
    robot = RobotSerial(port=ROBOT_PORT, baudrate=ROBOT_BAUDRATE)
    
    # Tenta conectar
    if not robot.connect():
        print("Falha na conexão. Verifique:")
        print(f"  - Porta: {ROBOT_PORT}")
        print(f"  - Baudrate: {ROBOT_BAUDRATE}")
        print("  - Cabo USB conectado?")
        print("  - Microcontrolador ligado?")
        return
    
    # Loop de teste
    print("\nRecebendo dados do robô (Ctrl+C para parar)...\n")
    
    try:
        frame_count = 0
        
        while True:
            frame_count += 1
            
            # Tenta ler dados
            data = robot.read_data()
            
            if data:
                # Imprime dados recebidos
                print(f"Frame {frame_count}:")
                print(f"  Encoder: L={data['encoder_left']:6d}  R={data['encoder_right']:6d}")
                print(f"  IMU:     ax={data['imu_ax']:7.2f}  ay={data['imu_ay']:7.2f}  az={data['imu_az']:7.2f}")
                print(f"  Motores: IL={data['motor_current_left']:6d}mA  IR={data['motor_current_right']:6d}mA")
                print(f"  PWM:     L={data['pwm_left']:4d}%  R={data['pwm_right']:4d}%")
                print(f"  Sensor:  {data['sensor_front']:3d}%")
                print()
            else:
                # Sem dados ainda
                print(f"Frame {frame_count}: Aguardando dados...")
            
            time.sleep(0.1)  # Aguarda 100ms antes de tentar novamente
            
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário")
    finally:
        robot.disconnect()
        print("Teste finalizado")


if __name__ == "__main__":
    main()
