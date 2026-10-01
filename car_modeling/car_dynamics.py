import math

class motor:
    """
    first order motor (in % of PWM): y(k+1) = a*y(k) + b*sat(u(k)) + c*q(k)
    """
    def __init__(self):
        self._y = 0
        self._a = 0
        self._b = 0
        self._c = 0

        self.dead_zone_const = 20
        self.magnetic_saturation_const = 90

    def set_constants(self, a, b, c):
        self._a = a
        self._b = b
        self._c = c

    def get_y(self):
        return self._y

    def saturate(self, u):
        # saturate output
        return max(-100, min(100, u))

    def dead_zone(self, u):
        # apply dead zone
        return u if abs(u) >= self.dead_zone_const else 0

    def magnetic_saturation(self, u):
        # apply magnetic saturation
        s = self.magnetic_saturation_const
        return u if abs(u) <= s else s + (u-s)/3

    # first ordem step response
    def step(self, u, q):
        #u = self.dead_zone(u)
        #u = self.magnetic_saturation(u)
        u = self.saturate(u)
        self._y = self._a * self._y + self._b * u + self._c * q

class car_dynamics:
    def __init__(self, z=0.1,  wheels_radius=0.04, wheels_distance=0.2, wheels_RPM=1000, ke_l=1, ke_r=1, kq=1, accommodation_time_l=1.0, accommodation_time_r=1.0):
        self.z = z

        self.v1 = 0
        self.v2 = 0
        self.q1 = 0
        self.q2 = 0
        self._wheels_radius = wheels_radius
        self._wheels_distance = wheels_distance

        # wheel speed in rad/s for 1% of PWM
        self._wheels_speed_rad_s = (2 * math.pi * wheels_RPM)/(60*100)

        # gains for calculating speed and omega
        self._gain_Vm = self._wheels_speed_rad_s * self._wheels_radius/2
        self._gain_Omega = self._wheels_speed_rad_s * self._wheels_radius/self._wheels_distance

        # gains for calculating normalized speed and omega
        self._gain_Vm_norm = 1/2
        self._gain_Omega_norm = 1/2

        # accommodation time (5 tau)
        self.tau_l = accommodation_time_l/5
        self.tau_r = accommodation_time_r/5

        # --- motor constants (using z transform) ---
        a1 = math.exp(-z/self.tau_l)
        a2 = math.exp(-z/self.tau_r)

        self._ml = motor()
        self._mr = motor()
        self._ml.set_constants(a1, ke_l * (1 - a1), kq * (1 - a1))
        self._mr.set_constants(a2, ke_r * (1 - a2), kq * (1 - a2))

    def _speed(self):
        return self._ml.get_y() + self._mr.get_y()

    def _omega(self):
        return self._ml.get_y() - self._mr.get_y()

    def speed_norm(self):
        return self._speed() * self._gain_Vm_norm

    def omega_norm(self):
        return self._omega() * self._gain_Omega_norm

    def speed(self):
        # linear speed in m/s
        return self._speed() * self._gain_Vm

    def omega(self):
        # angular speed in rad/s (positive turns right)
        return self._omega() * self._gain_Omega

    def get_space(self):
        """
        displacement of the step, used by the track (that rotates first and then moves).
        the lateral term compensates the rotation, so the car moves along the previous heading:
            theta(k+1) = theta(k) + Ts*omega(k+1)
            x(k+1) = x(k) + Ts*v(k+1)*sin(theta(k))
            y(k+1) = y(k) + Ts*v(k+1)*cos(theta(k))
        """
        space = self.speed() * self.z
        angle = self.omega() * self.z
        return space * math.sin(angle), space * math.cos(angle), angle

    def get_wheels_norm(self):
        # wheels speed in % of PWM
        return self._ml.get_y(), self._mr.get_y()

    def get_wheels_speed(self):
        # wheels speed in rad/s
        return self._ml.get_y() * self._wheels_speed_rad_s, self._mr.get_y() * self._wheels_speed_rad_s

    def step(self, u1, u2, q1, q2):
        self._ml.step(u1, q1)
        self._mr.step(u2, q2)
        self.v1 = u1
        self.v2 = u2
        self.q1 = q1
        self.q2 = q2

    def get_size(self):
        return self._wheels_distance
