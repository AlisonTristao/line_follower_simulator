"""
Exemplo: Como usar serial_com.py

Mostra os passos básicos para comunicação serial.
"""

from serial_com import SerialCom

# ============================================================================
# PASSO 1: Criar instância
# ============================================================================

com = SerialCom()


# ============================================================================
# PASSO 2: Listar portas disponíveis
# ============================================================================

print("Portas disponíveis:")
ports = com.list_ports()

if not ports:
    print("Nenhuma porta encontrada!")
    exit(1)


# ============================================================================
# PASSO 3: Conectar em uma porta
# ============================================================================

# Opção 1: Deixar usuário escolher
port = com.select_port()

# Opção 2: Conectar diretamente
# com.connect("COM3")

if not com.is_connected():
    print("Falha ao conectar!")
    exit(1)


# ============================================================================
# PASSO 4: Enviar mensagens
# ============================================================================

com.send_message("HELLO")  # Automaticamente adiciona \n
# ou
com.send_message("TEST\n")  # Já tem \n


# ============================================================================
# PASSO 5: Receber mensagens
# ============================================================================

# Uma única mensagem
msg = com.read_message()
if msg:
    print(f"Recebido: {msg}")


# Múltiplas mensagens em loop
while com.is_connected():
    msg = com.read_message()
    if msg:
        print(f"< {msg}")
        # Processar mensagem
        # Exemplo: atualizar gráficos


# ============================================================================
# PASSO 6: Desconectar
# ============================================================================

com.disconnect()


# ============================================================================
# INTEGRAÇÃO COMPLETA COM SIMULADOR
# ============================================================================

"""
No main.py (futuro), seria algo assim:

from serial_com import SerialCom

com = SerialCom()
com.select_port()
com.connect()

while True:
    # Recebe mensagem do robô
    msg = com.read_message()
    
    if msg:
        # Processa e atualiza gráficos
        # dados = parse_message(msg)
        # sim.update_robot_data(dados)
        pass
    
    # Simula como de costume
    data = sim.step(delta_x, delta_y)
    if data is None:
        break

com.disconnect()
"""
