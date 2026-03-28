"""
Módulo de comunicação serial com o robô microcontrolador.

Segue a metodologia simples e robusta do projeto.
Conecta na porta serial, recebe pacotes, retorna dados estruturados.
"""

import serial
import struct
from typing import Dict, Optional, Tuple


class RobotSerial:
    """
    Comunicação serial simples com o robô.
    
    Envia e recebe dados no protocolo:
    [Header: 0xFF] [Length] [Dados...] [Checksum]
    """
    
    HEADER = 0xFF
    TIMEOUT = 0.05  # 50ms timeout
    
    def __init__(self, port: str, baudrate: int = 115200):
        """
        Inicializa a comunicação serial.
        
        Args:
            port: Porto serial (ex: "COM3", "/dev/ttyUSB0")
            baudrate: Velocidade serial (padrão 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        
    def connect(self) -> bool:
        """
        Abre a conexão serial com o robô.
        
        Returns:
            True se conectou, False caso contrário
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.TIMEOUT
            )
            self.connected = True
            print(f"✓ Conectado ao robô em {self.port} ({self.baudrate} baud)")
            return True
        except serial.SerialException as e:
            print(f"✗ Erro ao conectar: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Fecha a conexão serial.
        
        Returns:
            True se desconectou, False caso contrário
        """
        if self.serial and self.connected:
            try:
                self.serial.close()
                self.connected = False
                print("✓ Desconectado do robô")
                return True
            except serial.SerialException as e:
                print(f"✗ Erro ao desconectar: {e}")
                return False
        return False
    
    @staticmethod
    def _checksum(data: bytes) -> int:
        """
        Calcula checksum XOR dos dados.
        
        Args:
            data: Bytes para calcular
            
        Returns:
            Checksum (1 byte)
        """
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum & 0xFF
    
    def _read_packet(self) -> Optional[bytes]:
        """
        Tenta ler um pacote válido da serial.
        
        Returns:
            Bytes do pacote ou None se inválido/timeout
        """
        if not self.connected or not self.serial:
            return None
        
        try:
            # Procura pelo header
            while self.serial.in_waiting > 0:
                byte = self.serial.read(1)
                
                if byte[0] == self.HEADER:
                    # Lê o tamanho do payload
                    length_byte = self.serial.read(1)
                    if len(length_byte) == 0:
                        continue
                    
                    length = length_byte[0]
                    
                    # Lê o payload + checksum
                    payload_and_checksum = self.serial.read(length + 1)
                    if len(payload_and_checksum) < length + 1:
                        continue
                    
                    # Reconstrói o pacote completo
                    packet = byte + length_byte + payload_and_checksum
                    
                    # Valida checksum
                    expected_checksum = packet[-1]
                    calculated_checksum = self._checksum(packet[:-1])
                    
                    if expected_checksum == calculated_checksum:
                        return packet
                    else:
                        print(f"⚠ Checksum inválido")
            
            return None
            
        except serial.SerialException as e:
            print(f"✗ Erro na leitura serial: {e}")
            self.connected = False
            return None
    
    def read_data(self) -> Optional[Dict]:
        """
        Lê um pacote de dados do robô.
        
        Returns:
            Dicionário com dados ou None se erro
        """
        packet = self._read_packet()
        if not packet:
            return None
        
        try:
            # Extrai o payload (ignora header, length, e checksum)
            payload = packet[2:-1]
            
            # Unpack dos dados (big-endian)
            # Estrutura: [encoder_left(2)] [encoder_right(2)] [imu_ax(2)] [imu_ay(2)] [imu_az(2)]
            #            [motor_i_left(2)] [motor_i_right(2)] [pwm_left(1)] [pwm_right(1)] [sensor(1)]
            
            if len(payload) < 17:  # Tamanho mínimo esperado
                return None
            
            offset = 0
            
            # Encoders (int16, big-endian)
            encoder_left = struct.unpack('>h', payload[offset:offset+2])[0]
            offset += 2
            
            encoder_right = struct.unpack('>h', payload[offset:offset+2])[0]
            offset += 2
            
            # IMU aceleração (int16, big-endian, em 0.01 m/s²)
            imu_ax = struct.unpack('>h', payload[offset:offset+2])[0] * 0.01
            offset += 2
            
            imu_ay = struct.unpack('>h', payload[offset:offset+2])[0] * 0.01
            offset += 2
            
            imu_az = struct.unpack('>h', payload[offset:offset+2])[0] * 0.01
            offset += 2
            
            # Motor corrente (int16, big-endian, em mA)
            motor_current_left = struct.unpack('>h', payload[offset:offset+2])[0]
            offset += 2
            
            motor_current_right = struct.unpack('>h', payload[offset:offset+2])[0]
            offset += 2
            
            # PWM (int8, sinalizado)
            pwm_left = struct.unpack('>b', payload[offset:offset+1])[0]
            offset += 1
            
            pwm_right = struct.unpack('>b', payload[offset:offset+1])[0]
            offset += 1
            
            # Sensor frontal (uint8)
            sensor_front = struct.unpack('>B', payload[offset:offset+1])[0]
            offset += 1
            
            # Monta dicionário de retorno
            return {
                "encoder_left": encoder_left,
                "encoder_right": encoder_right,
                "imu_ax": imu_ax,
                "imu_ay": imu_ay,
                "imu_az": imu_az,
                "motor_current_left": motor_current_left,
                "motor_current_right": motor_current_right,
                "pwm_left": pwm_left,
                "pwm_right": pwm_right,
                "sensor_front": sensor_front,
            }
            
        except (struct.error, IndexError) as e:
            print(f"✗ Erro ao parsear pacote: {e}")
            return None
    
    def send_data(self, data: bytes) -> bool:
        """
        Envia dados para o robô.
        
        Args:
            data: Bytes para enviar
            
        Returns:
            True se enviou, False caso contrário
        """
        if not self.connected or not self.serial:
            return False
        
        try:
            self.serial.write(data)
            return True
        except serial.SerialException as e:
            print(f"✗ Erro ao enviar dados: {e}")
            return False
    
    def send_command(self, pwm_left: int, pwm_right: int) -> bool:
        """
        Envia comando de controle PWM para o robô.
        
        Args:
            pwm_left: PWM motor esquerdo (-100 a 100)
            pwm_right: PWM motor direito (-100 a 100)
            
        Returns:
            True se enviou, False caso contrário
        """
        # Limita valores
        pwm_left = max(-100, min(100, pwm_left))
        pwm_right = max(-100, min(100, pwm_right))
        
        # Monta o pacote
        header = bytes([0xFE])  # Header diferente para comandos
        payload = struct.pack('>bb', pwm_left, pwm_right)
        checksum = bytes([self._checksum(header + payload)])
        
        packet = header + bytes([len(payload)]) + payload + checksum
        
        return self.send_data(packet)
    
    def is_connected(self) -> bool:
        """Retorna se está conectado."""
        return self.connected
