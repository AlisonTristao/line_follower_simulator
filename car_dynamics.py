import math
import random

class motor:
    def __init__(self):
        self._y = 0
        self._last_y = 0
        self._a = [0]
        self._b = [0]
        self._c = [0]
    
    def set_constants(self, a, b, c):
        self._a = a
        self._b = b
        self._c = c

    def saturate(self):
        if self._y > 100:
            self._y = 100
        elif self._y < -100:
            self._y = -100

    # delay 1 because u(k-1) and q(k-1)
    def get_y(self):
        return self._last_y

    # first ordem step response
    def step(self, u, q=0):
        self._last_y = self._y
        self._y = (self._a[0] * self._y + self._b[0] * u + self._c[0] * q)
        
        # saturate output
        self.saturate()
    
class car_dynamics:
    def __init__(self, z=0.1,  wheels_radius=0.04, wheels_distance=0.1, wheels_RPM=3000, ke=1, kq=1, accommodation_time=1.0):
        self.z = z
        self._wheels_radius = wheels_radius
        self._wheels_distance = wheels_distance
        self._wheels_RPM = wheels_RPM/100

        # last speed and omega
        self.last_speed = 0
        self.last_omega = 0

        # gains for calculating speed and omega
        self._gain_Vm = (self._wheels_RPM/60) * (self._wheels_radius/2)
        self._gain_Omega = (self._wheels_RPM/60) * self._wheels_radius/self._wheels_distance

        # gains for calculating normalized speed and omega
        self._gain_Vm_norm = (1/2)
        self._gain_Omega_norm = (1/2)

        # constants
        ke = 1
        kq = 1
        accommodation_time = 1.0
        self.tau = accommodation_time/5

        # motor objects
        self._ml = motor()
        # motor constants (using z transform)
        self._mr = motor()

        # --- motor constants (using z transform) ---

        # time constants
        a1 = math.exp(-z/self.tau)
        a2 = math.exp(-z/self.tau)

        # control gain
        b1 = ke * (1 - a1)
        b2 = ke * (1 - a2)

        # noise gain
        c1 = kq * (1 - a1)
        c2 = kq * (1 - a2)

        self._ml.set_constants([a1], [b1], [c1])
        self._mr.set_constants([a2], [b2], [c2])

    def _speed(self):
        return (self._ml.get_y() + self._mr.get_y())
    
    def _omega(self):
        return (self._ml.get_y() - self._mr.get_y())

    def speed_norm(self):
        return round(self._speed() * self._gain_Vm_norm, 2)
    
    def omega_norm(self):
        return round(self._omega() * self._gain_Omega_norm, 2)

    def speed(self):
        return round(self._speed() * self._gain_Vm, 2)
    
    def omega(self):
        return round(self._omega() * self._gain_Omega, 2)
    
    def get_space(self):
        # get the current speed and omega
        speed = self.speed()
        omega = self.omega()
        
        # calculate the space using trapezoidal rule
        space = (self.last_speed + speed) * self.z/2
        angle = (self.last_omega + omega) * self.z/2

        # update last speed and omega
        dx = space * math.sin(angle)
        dy = space * math.cos(angle)

        # update last speed and omega
        self.last_speed = speed
        self.last_omega = omega
        return dx, dy, angle

    def getWheels(self):
        return self._ml.get_y(), self._mr.get_y()

    def step(self, u1, u2, q1=0, q2=0):
        self._ml.step(u1, q1), self._mr.step(u2, q2)
        #return self.speed(), self.omega()

    def get_size(self):
        return self._wheels_distance