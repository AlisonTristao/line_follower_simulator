pkg load control
fps = 80
z = tf('z', 1/fps);

a = 0.94;
b = 0.06;
G = b/(1-a*z^(-1))

Kp = 1.0
Ki = 0.08
C = Kp + Ki/(1-z^(-1))

H = minreal(C*G/(1+C*G))

step(H)

pause;