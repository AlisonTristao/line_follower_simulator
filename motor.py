import numpy as np
import math 
import matplotlib.pyplot as plt

ke = 1.5
alpha = 0.8
beta = ke * (1 - alpha)

deadzone = 20
cte = 1e-8

u_array = []
for i in range(100):
    if i < deadzone:
        u = 0
    else:
        u = ke * (i - deadzone) * 1/(1 + cte * (i - deadzone)**4)

    u_array.append(u)


# plot the control signal
plt.plot(u_array)
plt.grid()
plt.show()
    


