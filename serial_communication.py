"""
Serial communication module for receiving data from the real robot microcontroller.

This module handles:
- Opening/closing serial connection
- Receiving data packets from the robot
- Parsing robot sensor data (encoder, IMU, motor current, PWM, etc.)
- Calculating delta_x, delta_y from odometry
"""

import serial
import struct
from typing import Dict, Tuple, Optional


class RobotSerialCommunication:
    """
    Handles serial communication with the robot microcontroller.
    
    Expected packet format from microcontroller (example):
    - Header (1 byte): 0xFF
    - Data length (1 byte)
    - Payload (N bytes):
        - encoder_left (2 bytes, int16)
        - encoder_right (2 bytes, int16)
        - imu_ax (2 bytes, int16)  # acceleration in 0.01 m/s²
        - imu_ay (2 bytes, int16)
        - imu_az (2 bytes, int16)
        - motor_current_left (2 bytes, int16)  # in mA
        - motor_current_right (2 bytes, int16)
        - pwm_left (1 byte, int8)  # -100 to 100%
        - pwm_right (1 byte, int8)
        - sensor_front (1 byte, uint8)  # 0-100%
    - Checksum (1 byte)
    """
    
    # Packet structure constants
    HEADER = 0xFF
    MIN_PACKET_SIZE = 20  # Header + length + data + checksum
    
    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 0.1):
        """
        Initialize serial communication.
        
        Args:
            port: Serial port name (e.g., "COM3" on Windows, "/dev/ttyUSB0" on Linux)
            baudrate: Baud rate for serial communication (default 115200)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        
        # Odometry tracking
        self.last_encoder_left = 0
        self.last_encoder_right = 0
        self.odometry_x = 0.0
        self.odometry_y = 0.0
        self.orientation = 0.0  # radians
        
        # Robot parameters (calibrate these values)
        self.WHEEL_RADIUS = 0.02  # meters
        self.WHEEL_DISTANCE = 0.15  # meters (distance between wheels)
        self.ENCODER_CPR = 512  # encoder counts per revolution
        
    def connect(self) -> bool:
        """
        Open serial connection to the robot.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE
            )
            self.is_connected = True
            print(f"Connected to robot at {self.port} ({self.baudrate} baud)")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to robot: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Close serial connection.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        if self.serial_connection and self.is_connected:
            try:
                self.serial_connection.close()
                self.is_connected = False
                print("Disconnected from robot")
                return True
            except serial.SerialException as e:
                print(f"Error disconnecting: {e}")
                return False
        return False
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate simple checksum (XOR of all bytes)."""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum & 0xFF
    
    def _parse_packet(self, packet: bytes) -> Optional[Dict]:
        """
        Parse a received data packet from the robot.
        
        Args:
            packet: Raw packet bytes
            
        Returns:
            Dictionary with parsed data or None if invalid packet
        """
        if len(packet) < self.MIN_PACKET_SIZE:
            return None
        
        # Check header
        if packet[0] != self.HEADER:
            return None
        
        # Check length
        length = packet[1]
        if len(packet) != length + 3:  # header + length + data + checksum
            return None
        
        # Verify checksum
        payload = packet[:-1]
        expected_checksum = packet[-1]
        calculated_checksum = self._calculate_checksum(payload)
        
        if calculated_checksum != expected_checksum:
            print(f"Checksum error: expected {expected_checksum}, got {calculated_checksum}")
            return None
        
        try:
            # Parse payload (adjust format based on your microcontroller's format)
            payload_data = packet[2:-1]
            
            # Unpack binary data (adjust format strings based on your protocol)
            encoder_left = struct.unpack('>h', payload_data[0:2])[0]  # signed int16
            encoder_right = struct.unpack('>h', payload_data[2:4])[0]
            
            imu_ax = struct.unpack('>h', payload_data[4:6])[0] * 0.01  # convert to m/s²
            imu_ay = struct.unpack('>h', payload_data[6:8])[0] * 0.01
            imu_az = struct.unpack('>h', payload_data[8:10])[0] * 0.01
            
            motor_current_left = struct.unpack('>h', payload_data[10:12])[0]  # mA
            motor_current_right = struct.unpack('>h', payload_data[12:14])[0]
            
            pwm_left = struct.unpack('>b', payload_data[14:15])[0]  # signed int8
            pwm_right = struct.unpack('>b', payload_data[15:16])[0]
            
            sensor_front = struct.unpack('>B', payload_data[16:17])[0]  # unsigned int8
            
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
            print(f"Error parsing packet: {e}")
            return None
    
    def _calculate_odometry(self, encoder_left: int, encoder_right: int) -> Tuple[float, float, float]:
        """
        Calculate delta_x, delta_y from encoder readings using odometry.
        
        Args:
            encoder_left: Left encoder count since last reading
            encoder_right: Right encoder count since last reading
            
        Returns:
            Tuple of (delta_x, delta_y, omega) in meters and rad/s
        """
        import math
        
        # Calculate wheel distances traveled
        dist_left = (encoder_left / self.ENCODER_CPR) * 2 * math.pi * self.WHEEL_RADIUS
        dist_right = (encoder_right / self.ENCODER_CPR) * 2 * math.pi * self.WHEEL_RADIUS
        
        # Calculate robot displacement
        dist_center = (dist_left + dist_right) / 2.0
        delta_theta = (dist_right - dist_left) / self.WHEEL_DISTANCE
        
        # Update orientation
        self.orientation += delta_theta
        
        # Calculate displacement in robot frame
        delta_x = dist_center * math.cos(self.orientation)
        delta_y = dist_center * math.sin(self.orientation)
        
        return delta_x, delta_y, delta_theta
    
    def receive_data(self) -> Optional[Tuple[Dict, float, float]]:
        """
        Try to receive and parse one data packet from the robot.
        
        Returns:
            Tuple of (sensor_data_dict, delta_x, delta_y) or None if no valid packet
        """
        if not self.is_connected or not self.serial_connection:
            return None
        
        try:
            # Try to find a valid packet
            # Look for header and read until we have a complete packet
            while self.serial_connection.in_waiting > 0:
                byte = self.serial_connection.read(1)
                
                if byte[0] == self.HEADER:
                    # Read length byte
                    length_byte = self.serial_connection.read(1)
                    if len(length_byte) == 0:
                        continue
                    
                    length = length_byte[0]
                    
                    # Read remaining packet (data + checksum)
                    remaining = self.serial_connection.read(length + 1)
                    
                    # Reconstruct full packet
                    packet = byte + length_byte + remaining
                    
                    # Parse packet
                    data = self._parse_packet(packet)
                    
                    if data:
                        # Calculate odometry
                        delta_x, delta_y, _ = self._calculate_odometry(
                            data["encoder_left"],
                            data["encoder_right"]
                        )
                        
                        return data, delta_x, delta_y
            
            return None
            
        except serial.SerialException as e:
            print(f"Serial communication error: {e}")
            self.is_connected = False
            return None
    
    def send_command(self, pwm_left: int, pwm_right: int) -> bool:
        """
        Send motor control command to the robot.
        
        Args:
            pwm_left: Left motor PWM (-100 to 100)
            pwm_right: Right motor PWM (-100 to 100)
            
        Returns:
            True if command sent successfully
        """
        if not self.is_connected or not self.serial_connection:
            return False
        
        # Clamp values
        pwm_left = max(-100, min(100, pwm_left))
        pwm_right = max(-100, min(100, pwm_right))
        
        try:
            # Create command packet
            header = bytes([0xFE])  # Different header for commands
            payload = struct.pack('>bb', pwm_left, pwm_right)
            checksum = bytes([self._calculate_checksum(header + payload)])
            
            packet = header + bytes([len(payload)]) + payload + checksum
            self.serial_connection.write(packet)
            
            return True
        except serial.SerialException as e:
            print(f"Failed to send command: {e}")
            return False
    
    def calibrate_odometry(self, encoders_per_cm: float):
        """
        Calibrate odometry parameters based on encoder resolution.
        
        Args:
            encoders_per_cm: Number of encoder counts per centimeter of travel
        """
        # This can be used to fine-tune wheel radius and encoder CPR
        pass


if __name__ == "__main__":
    # Test code
    robot_serial = RobotSerialCommunication(port="COM3")
    
    if robot_serial.connect():
        try:
            for i in range(100):
                result = robot_serial.receive_data()
                if result:
                    data, delta_x, delta_y = result
                    print(f"Frame {i}: encoder_left={data['encoder_left']}, "
                          f"delta_x={delta_x:.4f}, delta_y={delta_y:.4f}")
        except KeyboardInterrupt:
            print("Stopped by user")
        finally:
            robot_serial.disconnect()
    else:
        print("Could not connect to robot")
