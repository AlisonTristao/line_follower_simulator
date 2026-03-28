# Como Usar o Simulador

## 3 Modos Disponíveis

### 1️⃣ Modo Simulado (Sem Robô)

```bash
python main.py
```

- Gera dados aleatórios para testar gráficos
- Não precisa de robô conectado
- Bom para testes iniciais

---

### 2️⃣ Modo Teste Serial (Apenas Verificar Conexão)

```bash
python test_serial.py
```

- Testa se consegue se comunicar com o robô
- Imprime os dados recebidos no terminal
- Útil para diagnosticar problemas de conexão

**Antes de rodar:**
1. Conectar robô via USB
2. Identificar porta (COM3, /dev/ttyUSB0, etc.)
3. Editar `config_serial.py`:
   ```python
   ROBOT_PORT = "COM3"  # Alterar porta
   ```

**Saída esperada:**
```
✓ Conectado ao robô em COM3 (115200 baud)

Recebendo dados do robô (Ctrl+C para parar)...

Frame 1: Aguardando dados...
Frame 2: Aguardando dados...
Frame 3:
  Encoder: L=  1024  R=  1020
  IMU:     ax=   0.12  ay=  -0.05  az=   9.81
  ...
```

---

### 3️⃣ Modo Integrado (Simulador com Dados Reais)

```bash
python main_serial.py
```

- Abre o simulador visual
- Recebe dados reais do robô via serial
- Atualiza gráficos em tempo real
- Mostra posição do robô no track

**Antes de rodar:**
1. Conectar robô via USB
2. Configurar porta em `config_serial.py`
3. Rodar script

---

## Arquivo `main.py` (Original)

```bash
python main.py
```

- Simulação com dados aleatórios
- Não usa serial
- Otimizado para testes rápidos

---

## Arquivo `main_with_serial.py` (Antigo)

Não usar mais - use `main_serial.py` em sua lugar.

---

## Estrutura de Arquivos

```
├── main.py                 # Simulação com dados aleatórios
├── main_serial.py          # Simulação com dados reais (USE ESTE)
├── test_serial.py          # Teste de conexão serial
│
├── robot_serial.py         # Classe de comunicação serial
├── config_serial.py        # Configurações (porta, calibração)
│
├── simulator.py            # Engine do simulador
├── settings.py             # Configurações gerais
└── graphics/
    ├── graphics_elements.py
    └── track_generator.py
```

---

## Checklist para Usar com Robô Real

- [ ] Robô conectado via USB
- [ ] Microcontrolador programado com protocolo correto
- [ ] Porta identificada (COM3, /dev/ttyUSB0, etc.)
- [ ] `config_serial.py` com porta correta
- [ ] `pyserial` instalado (`conda install pyserial`)
- [ ] Rodar `python test_serial.py` primeiro para testar
- [ ] Se ok, rodar `python main_serial.py`

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| "Cannot open port" | Verificar porta em config_serial.py |
| "No module named 'serial'" | `conda install pyserial` |
| "Checksum error" | Verificar protocolo no microcontrolador |
| "Sem dados" | Microcontrolador enviando dados? |

---

## Próximas Etapas

1. Implementar envio de comandos PWM
2. Calcular odometria dos encoders
3. Filtrar dados da IMU
4. Salvar log de dados
