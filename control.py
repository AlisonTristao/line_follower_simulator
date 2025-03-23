class control:
    def __init__(self, kp=1, ki=1, kd=1, z=0.1):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.z = z
        self.last_error = 0
        self.integral = 0

    def _saturate_integrator(self, value):
        if value > 1:
            return 1
        if value < -1:
            return -1
        return value
    
    def _saturate(self, value):
        if value > 1:
            return 1
        if value < -1:
            return -1
        return value
    
    def _control(self, error):
        self.integral += error * self.z
        self.integral = self._saturate_integrator(self.integral)
        derivative = (error - self.last_error)/self.z
        self.last_error = error
        pid = self.kp * error + self.ki * self.integral + self.kd * derivative
        return self._saturate(pid)
    
    def control(self, error):
        return self._control(error)