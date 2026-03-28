"""
Comunicação serial simples com o robô.

Lista portas disponíveis, conecta, envia e recebe mensagens terminadas em \n
"""

import serial
import serial.tools.list_ports
from typing import Optional, List


class SerialCom:
    """Comunicação serial com o robô via mensagens terminadas em \\n"""
    
    BAUDRATE = 115200  # Definido aqui no código
    
    def __init__(self):
        """Inicializa comunicação serial."""
        self.serial = None
        self.connected = False
        self.port = None
    
    def list_ports(self) -> List[str]:
        """
        Lista todas as portas seriais disponíveis.
        
        Returns:
            Lista com os nomes das portas (ex: ["COM3", "COM4"])
        """
        ports = []
        for port, desc, hwid in serial.tools.list_ports.comports():
            ports.append(port)
        return ports
    
    def select_port(self) -> Optional[str]:
        """
        Mostra portas disponíveis e permite seleção do usuário.
        
        Returns:
            Porto selecionada ou None se nenhuma disponível
        """
        print("\n=== Portas Seriais Disponíveis ===")
        ports = self.list_ports()
        
        if not ports:
            print("Nenhuma porta serial encontrada!")
            return None
        
        print(f"\nTotal: {len(ports)} porta(s)")
        print("\nEscolha a porta:")
        
        try:
            choice = input("> ").strip()
            
            if choice in ports:
                self.port = choice
                return choice
            else:
                print(f"Porta '{choice}' não encontrada!")
                return None
        except KeyboardInterrupt:
            print("\nCancelado pelo usuário")
            return None
    
    def connect(self, port: Optional[str] = None) -> bool:
        """
        Conecta ao robô na porta especificada.
        
        Args:
            port: Porto serial (ex: "COM3"). Se None, usa última seleção.
            
        Returns:
            True se conectou, False caso contrário
        """
        if port:
            self.port = port
        
        if not self.port:
            return False
        
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.BAUDRATE,
                timeout=0.1
            )
            self.connected = True
            return True
        except serial.SerialException as e:
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Desconecta do robô.
        
        Returns:
            True se desconectou, False se erro
        """
        if self.serial and self.connected:
            try:
                self.serial.close()
                self.connected = False
                return True
            except serial.SerialException as e:
                return False
        return False
    
    def send_message(self, message: str) -> bool:
        """
        Envia uma mensagem para o robô.
        
        Mensagem é automaticamente terminada com \n
        
        Args:
            message: Texto da mensagem
            
        Returns:
            True se enviou, False caso contrário
        """
        if not self.connected or not self.serial:
            return False
        
        try:
            # Adiciona \n se não tiver
            if not message.endswith('\n'):
                message += '\n'
            
            self.serial.write(message.encode())
            return True
        except serial.SerialException as e:
            return False
    
    def read_message(self) -> Optional[str]:
        """
        Lê uma mensagem completa do robô (terminada em \n).
        
        Returns:
            String da mensagem sem o \n, ou None se nenhuma disponível
        """
        if not self.connected or not self.serial:
            return None
        
        try:
            if self.serial.in_waiting > 0:
                # Lê até encontrar \n
                line = self.serial.readline()
                if line:
                    # Decodifica e remove \n
                    message = line.decode().strip()
                    return message
            return None
        except serial.SerialException as e:
            return None
    
    def is_connected(self) -> bool:
        """Retorna se está conectado."""
        return self.connected
    
    def get_port(self) -> Optional[str]:
        """Retorna a porta atual conectada."""
        return self.port if self.connected else None


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def show_menu():
    """Mostra menu de opções."""
    print("\n=== Menu ===")
    print("1 - Listar portas")
    print("2 - Conectar")
    print("3 - Enviar mensagem")
    print("4 - Receber mensagens")
    print("5 - Desconectar")
    print("0 - Sair")
    print()


def main():
    """Função principal de teste."""
    com = SerialCom()
    
    while True:
        try:
            show_menu()
            choice = input("Opção: ").strip()
            
            if choice == "0":
                break
            
            elif choice == "1":
                print("\nPortas disponíveis:")
                com.list_ports()
            
            elif choice == "2":
                port = com.select_port()
                if port:
                    com.connect(port)
            
            elif choice == "3":
                if not com.is_connected():
                    print("Não conectado!")
                    continue
                msg = input("Mensagem: ").strip()
                if msg:
                    com.send_message(msg)
            
            elif choice == "4":
                if not com.is_connected():
                    print("Não conectado!")
                    continue
                print("\nRecebendo mensagens (Ctrl+C para parar)...")
                try:
                    while True:
                        msg = com.read_message()
                        if msg:
                            print(f"< {msg}")
                except KeyboardInterrupt:
                    print("\nParado")
            
            elif choice == "5":
                com.disconnect()
        
        except KeyboardInterrupt:
            print("\n\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {e}")
    
    com.disconnect()


if __name__ == "__main__":
    main()
