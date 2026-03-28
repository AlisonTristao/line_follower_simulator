from serial_com import SerialCom
import threading

def main() -> None:
    # ------------------------------------------------------------------
    # Serial Communication Interface
    # ------------------------------------------------------------------

    # Initialize serial communication
    com = SerialCom()
    
    print("\n" + "="*60)
    print("LINHA FOLLOWER - SERIAL COMMUNICATION TEST")
    print("="*60)
    
    # List and select port
    port = com.select_port()
    if not port:
        print("\n✗ Nenhuma porta selecionada. Encerrando.")
        return
    
    # Try to connect
    if not com.connect(port):
        print("\n✗ Falha ao conectar. Encerrando.")
        return
    
    print("\n✓ Conexão estabelecida com o robô!")
    print("\nComandos:")
    print("  - Digite mensagens para enviar")
    print("  - Digite 'sair' para desconectar")
    print("  - Digite 'limpar' para limpar tela")
    print("\n" + "="*60)
    
    frame_count = 0
    
    def read_messages():
        """Thread para ler mensagens do robô continuamente"""
        nonlocal frame_count
        while com.is_connected():
            msg = com.read_message()
            if msg:
                frame_count += 1
                print(f"\n[RX {frame_count}]: {msg}")
                print("> ", end="", flush=True)
    
    # Start read thread
    read_thread = threading.Thread(target=read_messages, daemon=True)
    read_thread.start()
    
    # Input loop
    try:
        while com.is_connected():
            try:
                msg = input("> ").strip()
                
                if msg.lower() == "sair":
                    print("\nDesconectando...")
                    break
                
                if msg.lower() == "limpar":
                    print("\n" * 50)
                    continue
                
                if msg:
                    com.send_message(msg)
                    print(f"[TX]: {msg}")
            
            except KeyboardInterrupt:
                print("\n\nDesconectando...")
                break
    
    finally:
        com.disconnect()
        print("✓ Desconectado.")

if __name__ == "__main__":
    main()
