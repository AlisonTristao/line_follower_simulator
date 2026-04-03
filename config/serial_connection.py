"""
Simple serial communication with the robot.

Lists available ports, connects, sends and receives newline-terminated messages.
"""

from typing import List, Optional

import serial
import serial.tools.list_ports


class SerialConnection:
    """Serial communication with newline-terminated messages."""

    BAUDRATE = 115200

    def __init__(self):
        """Initialize serial communication state."""
        self.serial = None
        self.connected = False
        self.port = None

    def list_ports(self) -> List[str]:
        """List all available serial ports."""
        return [port for port, _, _ in serial.tools.list_ports.comports()]

    def select_port(self) -> Optional[str]:
        """Display available ports and read user selection."""
        print("\n=== Available Serial Ports ===")
        ports = self.list_ports()

        if not ports:
            print("No serial ports found.")
            return None

        print(f"\nTotal: {len(ports)} port(s)")
        print("\nSelect a port:")

        try:
            choice = input("> ").strip()

            if choice in ports:
                self.port = choice
                return choice

            print(f"Port '{choice}' not found.")
            return None
        except KeyboardInterrupt:
            print("\nCancelled by user.")
            return None

    def connect(self, port: Optional[str] = None) -> bool:
        """Connect to the robot on the selected serial port."""
        if port:
            self.port = port

        if not self.port:
            return False

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.BAUDRATE,
                timeout=0.1,
            )
            self.connected = True
            return True
        except serial.SerialException:
            self.connected = False
            return False

    def disconnect(self) -> bool:
        """Disconnect from the robot."""
        if self.serial and self.connected:
            try:
                self.serial.close()
                self.connected = False
                return True
            except serial.SerialException:
                return False
        return False

    def send_message(self, message: str) -> bool:
        """Send a message to the robot. Automatically appends \n when missing."""
        if not self.connected or not self.serial:
            return False

        try:
            if not message.endswith("\n"):
                message += "\n"

            self.serial.write(message.encode())
            return True
        except serial.SerialException:
            return False

    def read_message(self) -> Optional[str]:
        """Read a full message from the robot (newline terminated)."""
        if not self.connected or not self.serial:
            return None

        try:
            if self.serial.in_waiting > 0:
                line = self.serial.readline()
                if line:
                    return line.decode().strip()
            return None
        except serial.SerialException:
            return None

    def is_connected(self) -> bool:
        """Return True when connected."""
        return self.connected

    def get_port(self) -> Optional[str]:
        """Return the currently connected port."""
        return self.port if self.connected else None


def show_menu():
    """Display the interactive CLI menu."""
    print("\n=== Menu ===")
    print("1 - List ports")
    print("2 - Connect")
    print("3 - Send message")
    print("4 - Receive messages")
    print("5 - Disconnect")
    print("0 - Exit")
    print()


def main():
    """Standalone test entrypoint."""
    connection = SerialConnection()

    while True:
        try:
            show_menu()
            choice = input("Option: ").strip()

            if choice == "0":
                break

            if choice == "1":
                print("\nAvailable ports:")
                for port_name in connection.list_ports():
                    print(port_name)

            elif choice == "2":
                port = connection.select_port()
                if port:
                    connection.connect(port)

            elif choice == "3":
                if not connection.is_connected():
                    print("Not connected.")
                    continue
                msg = input("Message: ").strip()
                if msg:
                    connection.send_message(msg)

            elif choice == "4":
                if not connection.is_connected():
                    print("Not connected.")
                    continue
                print("\nReceiving messages (Ctrl+C to stop)...")
                try:
                    while True:
                        msg = connection.read_message()
                        if msg:
                            print(f"< {msg}")
                except KeyboardInterrupt:
                    print("\nStopped")

            elif choice == "5":
                connection.disconnect()

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as exc:
            print(f"Error: {exc}")

    connection.disconnect()


if __name__ == "__main__":
    main()
