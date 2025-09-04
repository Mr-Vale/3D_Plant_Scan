import logging
import time
from drivers.HR8825 import HR8825

logger = logging.getLogger(__name__)

class TurntableController:
    """
    Controls a NEMA 17 stepper motor via Waveshare Stepper Motor HAT (B) using HR8825 driver.
    Supports configurable microstepping and angle-based movement.
    """

    def __init__(
        self,
        steps_per_rev=200,
        microsteps=32,
        dir_pin=13,
        step_pin=19,
        enable_pin=12,
        mode_pins=(16, 17, 20),
        microstep_mode='softward',
        microstep_format='1/32step',
        step_delay=0.005
    ):
        self.steps_per_rev = steps_per_rev
        self.microsteps = microsteps
        self.total_steps_per_rev = self.steps_per_rev * self.microsteps
        self.current_step = 0
        self.motor = HR8825(
            dir_pin=dir_pin,
            step_pin=step_pin,
            enable_pin=enable_pin,
            mode_pins=mode_pins
        )
        self.step_delay = step_delay
        self.motor.SetMicroStep(microstep_mode, microstep_format)
        logger.info(
            f"TurntableController initialized (steps/rev={steps_per_rev}, microsteps={microsteps}, total_steps/rev={self.total_steps_per_rev}, pins={dir_pin, step_pin, enable_pin, mode_pins}, microstep={microstep_mode}:{microstep_format}, step_delay={step_delay})"
        )

    def move_to_step(self, step):
        """
        Move the turntable to the specified step (absolute position, in microsteps).
        """
        target = step % self.total_steps_per_rev
        steps_to_move = target - self.current_step
        direction = 'forward' if steps_to_move >= 0 else 'backward'
        steps = abs(steps_to_move)
        logger.info(
            f"Moving from step {self.current_step} to {target} ({steps} microsteps, dir={direction})"
        )
        if steps > 0:
            try:
                self.motor.TurnStep(Dir=direction, steps=steps, stepdelay=self.step_delay)
                self.current_step = target
            except Exception as e:
                logger.error(f"Error moving to step {step}: {str(e)}")

    def move_degrees(self, degrees):
        """
        Move the turntable by a specific number of degrees (positive: forward, negative: backward).
        """
        steps_to_move = int((degrees / 360.0) * self.total_steps_per_rev)
        direction = 'forward' if steps_to_move >= 0 else 'backward'
        steps = abs(steps_to_move)
        logger.info(
            f"Moving by {degrees} degrees ({steps} microsteps, dir={direction})"
        )
        if steps > 0:
            try:
                self.motor.TurnStep(Dir=direction, steps=steps, stepdelay=self.step_delay)
                self.current_step = (self.current_step + steps_to_move) % self.total_steps_per_rev
            except Exception as e:
                logger.error(f"Error moving by {degrees} degrees: {str(e)}")

    def reset_position(self):
        """
        Return the turntable to its starting position (absolute step 0).
        """
        if self.current_step != 0:
            steps_to_move = -self.current_step
            degrees_to_move = steps_to_move * (360.0 / self.total_steps_per_rev)
            logger.info(f"Resetting position by moving {degrees_to_move} degrees ({steps_to_move} microsteps)")
            self.move_degrees(degrees_to_move)

    def get_position_degrees(self):
        """
        Get the current position in degrees, relative to start.
        """
        return (self.current_step * 360.0) / self.total_steps_per_rev

    def cleanup(self):
        """
        Stop the motor and perform any required cleanup.
        """
        try:
            self.motor.Stop()
            logger.info("TurntableController cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")