import logging
import math
from random import randrange

from cares_lib.dynamixel.gripper_configuration import GripperConfig
from configurations import GripperEnvironmentConfig
from environments.two_finger.two_finger import TwoFingerTask

from cares_lib.dynamixel.Servo import Servo, DynamixelServoError
from cares_lib.dynamixel.Gripper import GripperError

class TwoFingerTranslation(TwoFingerTask):
    def __init__(
        self,
        env_config: GripperEnvironmentConfig,
        gripper_config: GripperConfig,
    ):
        self.noise_tolerance = env_config.noise_tolerance

        # These bounds are respective to the reference marker in Environment
        self.goal_min = [-30.0, 60.0]
        self.goal_max = [120.0, 110.0]

        logging.debug(
            f"Goal Min: {self.goal_min} Goal Max: {self.goal_max} Tolerance: {self.noise_tolerance}"
        )

        super().__init__(env_config, gripper_config)

    # overriding method
    def _choose_goal(self):
        x1, y1 = self.goal_min
        x2, y2 = self.goal_max

        goal_x = randrange(x1, x2)
        goal_y = randrange(y1, y2)

        return [goal_x, goal_y]

    # overriding method
    def _environment_info_to_state(self, environment_info):
        state = []

        # Servo Angles - Steps
        state += environment_info["gripper"]["positions"]

        # Servo Velocities - Steps per second
        if self.action_type == "velocity":
            state += environment_info["gripper"]["velocities"]

        # Servo + Two Finger Tips - X Y mm
        for i in range(1, self.gripper.num_motors + 3):
            servo_position = environment_info["poses"]["gripper"][i]
            state += self._pose_to_state(servo_position)

        # Object - X Y mm
        state += self._pose_to_state(environment_info["poses"]["object"])

        # Goal State - X Y mm
        state += self.goal

        return state

    # overriding method
    def _reward_function(self, previous_environment_info, current_environment_info):
        done = False

        reward = 0

        target_goal = current_environment_info["goal"]

        object_previous = previous_environment_info["poses"]["object"]["position"][0:2]
        object_current = current_environment_info["poses"]["object"]["position"][0:2]

        goal_distance_before = math.dist(target_goal, object_previous)
        goal_distance_after = math.dist(target_goal, object_current)

        goal_progress = goal_distance_before - goal_distance_after

        # The following step might improve the performance.

        # goal_before_array = goal_before[0:2]
        # delta_changes   = np.linalg.norm(target_goal - goal_before_array) - np.linalg.norm(target_goal - goal_after_array)
        # if -self.noise_tolerance <= delta_changes <= self.noise_tolerance:
        #     reward = -10
        # else:
        #     reward = -goal_difference
        #     #reward = delta_changes / (np.abs(yaw_before - target_goal))
        #     #reward = reward if reward > 0 else 0

        # For Translation. noise_tolerance is 15, it would affect the performance to some extent.
        if goal_distance_after <= self.noise_tolerance:
            logging.info("----------Reached the Goal!----------")
            done = True
            reward = 500
        else:
            reward += goal_progress

        logging.debug(
            f"Object Pose: {object_current} Goal Pose: {target_goal} Reward: {reward}"
        )

        return reward, done


class TwoFingerTranslationFlat(TwoFingerTranslation):
    def __init__(
        self,
        env_config: GripperEnvironmentConfig,
        gripper_config: GripperConfig,
    ):
        super().__init__(env_config, gripper_config)

    # overriding method
    def _reset(self):
        self.gripper.wiggle_home()


class TwoFingerTranslationSuspended(TwoFingerTranslation):
    def __init__(
        self,
        env_config: GripperEnvironmentConfig,
        gripper_config: GripperConfig,
    ):
        super().__init__(env_config, gripper_config)
        led = id = 5
        self.max_value = 3500
        self.min_value = 0
        servo_type = "XL330-M077-T"
        speed_limit = torque_limit = 150
        
        try:
            self.lift_servo = Servo(self.gripper.port_handler, self.gripper.packet_handler, self.gripper.protocol, id, led,
                                            torque_limit, speed_limit, self.max_value,
                                            self.min_value, servo_type)
            self.lift_servo.enable()
            print(self.lift_servo.current_velocity())
            # self.lift_servo.packet_handler.write4ByteTxRx(self.lift_servo.port_handler, self.lift_servo.motor_id, 112, self.lift_servo.max_velocity)
        except (GripperError, DynamixelServoError) as error:
            raise GripperError(f"Gripper#{self.gripper_id}: Failed to initialise lift servo") from error
        
    
    # overriding method
    def _reset(self):
        self.gripper.wiggle_home()
        self.grab_cube()

    
    def lift_up(self):
        self.lift_servo.move(self.max_value)

    def lift_down(self):
        self.lift_servo.move(self.min_value)

    def grab_cube(self):
        self.lift_up()
        self.gripper.move([512,362,512,662])
        self.lift_down()
