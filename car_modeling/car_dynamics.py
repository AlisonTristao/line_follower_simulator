import math

class motor:
    def __init__(self):
        self._y = 0
        self._a = [0]
        self._b = [0]
        self._c = [0]
    
    def set_constants(self, a, b, c):
        self._a = a
        self._b = b
        self._c = c

        self.dead_zone_const = 20
        self.magnetic_saturation_const = 90

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

        # calculate the step
        self._y = (self._a[0] * self._y + self._b[0] * u + self._c[0] * q)
    
class car_dynamics:
    def __init__(self, z=0.1,  wheels_radius=0.04, wheels_distance=0.2, wheels_RPM=1000, ke_l=1, ke_r=1, kq=1, accommodation_time_l=1.0, accommodation_time_r=1.0):
        self.z = z

        self.v1 = 0
        self.v2 = 0
        self.q1 = 0
        self.q2 = 0
        self._wheels_radius = wheels_radius
        self._wheels_distance = wheels_distance
        self._wheels_speed_rad_s = (2 * math.pi * wheels_RPM)/(60*100) # divide by 100
        
        # y
        self.__distance = 0
        self.__theta = 0

        # y'
        self.__speed = 0
        self.__omega = 0

        # y''
        self.__acceleration = 0
        self.__alpha = 0

        # enconders precision (angle per pulse)
        self._encoders_precision = 2 * math.pi/70
        self._theta_left = 0
        self._theta_right = 0

        # last speed and omega
        self.last_speed = 0
        self.last_omega = 0

        # gains for calculating speed and omega
        self._gain_Vm = (self._wheels_speed_rad_s) * (self._wheels_radius/2)
        self._gain_Omega = (self._wheels_speed_rad_s) * self._wheels_radius/self._wheels_distance

        # gains for calculating normalized speed and omega
        self._gain_Vm_norm = (1/2)
        self._gain_Omega_norm = (1/2)

        # accommodation time 
        self.tau_l = accommodation_time_l/5
        self.tau_r = accommodation_time_r/5

        # motor objects
        self._ml = motor()
        # motor constants (using z transform)
        self._mr = motor()

        # --- motor constants (using z transform) ---

        # time constants
        a1 = math.exp(-z/self.tau_l)
        a2 = math.exp(-z/self.tau_r)

        # control gain
        b1 = ke_l * (1 - a1)
        b2 = ke_r * (1 - a2)

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
        return self._speed() * self._gain_Vm_norm
    
    def omega_norm(self):
        return self._omega() * self._gain_Omega_norm

    def speed(self):
        return self._speed() * self._gain_Vm
    
    def omega(self):
        return self._omega() * self._gain_Omega

    def calculate_out_data(self):
        # get the current speed and omega
        self.__speed = self.speed()
        self.__omega = self.omega()
        self._theta_left += self._ml.get_y() * self._wheels_speed_rad_s * self.z
        self._theta_right += self._mr.get_y() * self._wheels_speed_rad_s *  self.z
        
        # calculate the space using trapezoidal rule
        self.__distance += self.__speed * self.z #(self.last_speed + speed) * self.z/2
        self.__theta += self.__omega * self.z #(self.last_omega + omega) * self.z/2

        # calculate the alpha and acceleration
        self.__acceleration = (self.__speed - self.last_speed)/self.z
        self.__alpha = (self.__omega - self.last_omega)/self.z

    def get_data(self):
        return self.__distance, self.__theta, self.__speed, self.__omega, self.__acceleration, self.__alpha

    def get_delta_space(self):
        # update last speed and omega
        dx = self.__distance  * math.sin(self.__theta)
        dy = self.__distance  * math.cos(self.__theta)

        # update last speed and omega
        self.last_speed = self.__speed
        self.last_omega = self.__omega

        return dx, dy, self.__theta
    
    def get_encoders(self):
        # calculate the pulses
        pulses_left = int(self._theta_left/self._encoders_precision)
        pulses_right = int(self._theta_right/self._encoders_precision)
        return pulses_left, pulses_right
    
    def get_accelerometer(self):
        # return the acceleration in x and y axis
        ax = self.__acceleration * math.sin(self.__theta)
        ay = self.__acceleration * math.cos(self.__theta)

        return ax, ay
    
    def get_gyroscope(self):
        # return the angular velocity
        return self.__omega
    
    def get_optical_flow(self):
        # return the speed in x and y axis
        vx = self.__speed * math.sin(self.__theta)
        vy = self.__speed * math.cos(self.__theta)

        return vx, vy
    
    def get_compass(self):
        # return the angle
        return self.__theta

    def _get_wheels(self):
        return self._ml.get_y(), self._mr.get_y()
    
    def get_wheels_norm(self):
        return self._get_wheels()

    def get_wheels_speed(self):
        return self._ml.get_y(), self._mr.get_y()

    def step(self, u1, u2, q1, q2):
        # saturate
        #u1 = max(-100, min(100, u1))
        #u2 = max(-100, min(100, u2))

        self._ml.step(u1, q1), self._mr.step(u2, q2)
        self.v1 = u1
        self.v2 = u2
        self.q1 = q1
        self.q2 = q2
        #return self.speed(), self.omega()

    def get_size(self):
        return self._wheels_distance