"""
Main com comunicação serial real do robô.

Este arquivo recebe dados reais via serial e atualiza o simulador.
"""

from robot_serial import RobotSerial
from config_serial import ROBOT_PORT, ROBOT_BAUDRATE
from settings import *
import time


def main_serial(sim):
    """
    Loop principal com comunicação serial real.
    
    Args:
        sim: Instância do GameSimulation
    """
    
    # Criar e conectar ao robô
    robot = RobotSerial(port=ROBOT_PORT, baudrate=ROBOT_BAUDRATE)
    
    if not robot.connect():
        print("Falha ao conectar ao robô!")
        print(f"Verificar porta: {ROBOT_PORT}")
        return
    
    frame_count = 0
    data_timeout_count = 0
    
    try:
        print("\nSimulador aguardando dados do robô...")
        print("Pressione ESC na janela do simulador para sair\n")
        
        while True:
            frame_count += 1
            
            delta_x = 0.0
            delta_y = 0.0
            
            # Tenta ler dados do robô
            robot_data = robot.read_data()
            
            if robot_data:
                # Dados recebidos - atualizar simulador
                sim.update_robot_data(robot_data)
                sim.update_graphs_from_robot_data()
                data_timeout_count = 0  # Reseta timeout
                
                # Debug a cada 10 frames
                if frame_count % 10 == 0:
                    print(f"Frame {frame_count}: Recv encoder_left={robot_data['encoder_left']:6d} sensor={robot_data['sensor_front']:3d}%")
            else:
                # Sem dados
                data_timeout_count += 1
                if data_timeout_count > 100:  # 5 segundos de timeout
                    print(f"Frame {frame_count}: ⚠ Sem dados do robô (timeout)")
                    data_timeout_count = 0
            
            # Step do simulador
            data = sim.step(delta_x, delta_y)
            if data is None:
                break
            
            # Desempacota dados de visualização
            line, future_pts = data
            
            # TODO: Enviar comando de controle para o robô
            # robot.send_command(pwm_left, pwm_right)
            
    except KeyboardInterrupt:
        print("\n\nSimulador interrompido pelo usuário")
    except Exception as e:
        print(f"\nErro no simulador: {e}")
    finally:
        robot.disconnect()
        print("Simulador finalizado")


if __name__ == "__main__":
    sim = settings()
    main_serial(sim)
