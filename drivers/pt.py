from HR8825 import HR8825
import time

# Initialize Motor1 with your pin mapping
Motor1 = HR8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))

# Set microstepping to full step (all DIP switches OFF for 'softward' mode)
Motor1.SetMicroStep('softward', 'fullstep')

# Move stepper 1 step forward every second for 200 steps
for i in range(200):
    Motor1.TurnStep(Dir='forward', steps=1, stepdelay=0.005)
    time.sleep(0.5)

# Optional: return to start position by moving 200 steps backward
#for i in range(200):
#    Motor1.TurnStep(Dir='backward', steps=1, stepdelay=0.005)
#    time.sleep(1)

Motor1.Stop()