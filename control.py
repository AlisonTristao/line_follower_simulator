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
    
if __name__ == "__main__":
    # screen settings => sizes FULL, MEDIUM, SMALL
    screen_size = MEDIUM
    screen_fps = 80
    track_seed = 1111

    # car constants
    wheels_radius       = 0.04  # meters
    wheels_distance     = 0.10  # meters
    wheels_RPM          = 1000  # RPM
    sensor_distance     = 0.10  # meters
    sensor_count        = 15    

    # motor constants
    ke                  = 1.0 # static gain of V1 => (y = ke * v)
    accommodation_time  = 1.0 # seconds

    # track caracteristics
    track_type          = CIRCLE
    track_length        = 0.015 # meters
    sensor_spacing      = 0.008 # meters

    # future points
    future_points       = 5     # number of future points
    future_spacing      = 30    # resolutuin of the track

    # setup the simulation
    start_simulation(screen_size, screen_fps, seed=track_seed, track_type=track_type, track_length=track_length, sensor_spacing=sensor_spacing)

    # setup the car dynamics
    set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, accommodation_time, sensor_distance, sensor_count)

    # setup the future points
    set_future_points(future_points, future_spacing)

    # --- insert your code here --- #
    v1 = 0
    v2 = 0

    Vm_ref = 1
    kp_1 = 1.0
    ki_1 = 0.08
    z_1 = 1/80
    control_vm = Control(kp_1, ki_1, z_1)

    omega_ref = 1
    kp_2 = 1.0
    ki_2 = 0.08
    z_2 = 1/80
    control_omega = Control(kp_2, ki_2, z_2)

    counter = 0
    arr_speed = []
    arr_omega = []
    arr_time = []
    while True:
        # --- step the simulation here --- #
        line, future_points, speed, omega = step_simulation(v1, v2)
        if line is None or future_points is None:
            break

        arr_speed.append(speed)
        arr_omega.append(omega)

        erro_vm = Vm_ref - speed
        v1 = control_vm.control(erro_vm)
        v2 = v1

        erro_omega = omega_ref - omega
        omega = control_omega.control(erro_omega)
        v1 += omega
        v2 -= omega

        counter += 1
        arr_time.append(counter/80)

        if counter == int(2*80):
            pygame.quit()
            break

        # --- calculate control here --- #
    # plot
    plt.title("degrau response")
    plt.plot(arr_time, arr_speed, label="speed", color="red", linestyle="-")
    plt.plot(arr_time, arr_omega, label="omega", color="blue", linestyle="--")
    plt.grid()
    plt.legend()
    plt.show()