pkg load control

horizon = 40;

fps = 80;
z = tf('z', 1/fps);
z_inv = tf('z^-1', 1/fps);

% delta
delta = z - 1;

% motors constant
alpha_left  = 0.90411;
alpha_right = 0.89784;
beta_left   = 0.086;
beta_right  = 0.102;

% wheels
sistem_left = beta_left/(z-alpha_left);
sistem_right = beta_right/(z-alpha_right);

% system to delta_u control
sistem_left = sistem_left * (1/delta)^2 %* (z_inv / z_inv)
sistem_right = sistem_right * (1/delta)^2 %* (z_inv / z_inv)

%step(sistem_left, sistem_right, 1)
%impulse(sistem_left, sistem_right, 1)

% Pega coeficientes numerador e denominador
den_left = sistem_left.den{1}(2:end) * -1;
den_right = sistem_right.den{1}(2:end) * -1;

m_left = [den_left;1, 0, 0; 0, 1, 0];
m_right = [den_right;1, 0, 0;0, 1, 0];

resultados = [];

for i = 1:horizon
    linha1_l = (m_left^i)(1, :);
    linha1_r = (m_right^i)(1, :);
    linha = [linha1_l, linha1_r];
    resultados = [resultados; linha];
end

csvwrite('coeffs.csv', resultados);

pause(5)