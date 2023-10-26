from environments.Environment import Environment
import logging
import numpy as np

from pathlib import Path
file_path = Path(__file__).parent.resolve()

from configurations import GripperEnvironmentConfig, ObjectConfig
from cares_lib.dynamixel.gripper_configuration import GripperConfig


class TranslationEnvironment(Environment):
    def __init__(self, env_config : GripperEnvironmentConfig, gripper_config : GripperConfig, object_config: ObjectConfig):
        super().__init__(env_config, gripper_config, object_config)
        self.goal_state = self.get_object_state()

   # overriding method
    def choose_goal(self):
        position = self.get_object_state()[0:2]
        position[0] = np.random.randint(225,450)
        position[1] = np.random.randint(150,225)

        return position

    def reward_function(self, target_goal, goal_before, goal_after):
        if goal_before is None:
            logging.debug("Start Marker Pose is None")
            return 0, True

        if goal_after is None:
            logging.debug("Final Marker Pose is None")
            return 0, True
        done = False

        target_goal = np.array(target_goal[0:2])
        goal_after_array = np.array(goal_after[0:2])
        goal_difference = np.linalg.norm(target_goal - goal_after_array)
    

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
        if goal_difference <= self.noise_tolerance:
            logging.info("----------Reached the Goal!----------")
            done = True
            reward = 500
        else:
            reward = -goal_difference
            
        logging.info(f"Reward: {reward}, Goal after: {goal_after_array}")

        return reward, done
    
    def ep_final_distance(self):
        return np.linalg.norm(np.array(self.goal_state) - np.array(self.get_object_state()[0:2]))
    
    def add_goal(self, state):
        state.append(self.goal_state[0])
        state.append(self.goal_state[1])
        return state
    
    def env_render(self, done=False, step=1, episode=1, mode="Exploration"):
        image = self.camera.get_frame()
        color = (0, 255, 0)
        if done:
            color = (0, 0, 255)

        target = (int(self.goal_pixel[0]), int(self.goal_pixel[1]))
        text_in_target = (
            int(self.goal_pixel[0]) - 15, int(self.goal_pixel[1]) + 3)
        cv2.circle(image, target, 18, color, -1)
        cv2.putText(image, 'Target', text_in_target,cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, f'Episode : {str(episode)}', (30, 40),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, f'Steps : {str(step)}', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, f'Success Counter : {str(self.counter_success)}', (400, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, f'Stage : {mode}', (900, 60),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA)
        cv2.imshow("State Image", image)
        cv2.waitKey(10)

    

