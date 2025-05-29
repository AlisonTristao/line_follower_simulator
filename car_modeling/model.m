pkg load control

horizon = 200;

fps = 80;
Ts = 1/fps;
z = tf('z', Ts);
z_inv = tf('z^-1', Ts);

% delta
delta = (z - 1);

% beta = Ke/(1 - alpha)
% Ke = 2pi * RPM/60 * 1/100

Ke = 2 * pi * 1000 / 60 * 1/100; % RPM = 1000 

% motors constant
alpha_left  = 0.90411;
alpha_right = 0.89784;
beta_left   = Ke*(1 - alpha_left);
beta_right  = Ke*(1 - alpha_right);

% wheels
sl = beta_left/(z-alpha_left) * z/delta * Ts
sr = beta_right/(z-alpha_right) * z/delta * Ts

% system to delta_u control
system_left = sl * 1/delta %* (z_inv / z_inv)
system_right = sr * 1/delta %* (z_inv / z_inv)

% Pega coeficientes numerador e denominador
den_left = system_left.den{1}(2:end) * -1;
den_right = system_right.den{1}(2:end) * -1;

m_left = [den_left;1, 0, 0; 0, 1, 0];
m_right = [den_right;1, 0, 0; 0, 1, 0];

resultados = [];

for i = 1:horizon
    linha1_l = (m_left^i)(1, :);
    linha1_r = (m_right^i)(1, :);
    linha = [linha1_l, linha1_r];
    resultados = [resultados; linha];
end

g_l = step(sl, (horizon)/fps);
g_r = step(sr, (horizon)/fps);

% transforma em colunas
g_l = g_l(:);
g_r = g_r(:);

% concatena horizontalmente
g = [g_l, g_r];

csvwrite('coeffs.csv', resultados);
csvwrite('g.csv', g);

%pause(5)