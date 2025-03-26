from simulator import *
import matplotlib.pyplot as plt

class Control:
    def __init__(self, kp=1, ki=1, z=0.1):
        self.kp = kp
        self.ki = ki
        self.z = z 
        self.integral = 0
        self.last_error = 0

    def _saturate(self, value):
        if value > 100:
            return 100
        if value < -100:
            return -100
        return value
    
    def _control(self, error):
        self.integral += error
        self.integral = self._saturate(self.integral)
        pid = self.kp * error +  self.integral * self.ki 
        return self._saturate(pid) 
    
    def control(self, error):
        return self._control(error)