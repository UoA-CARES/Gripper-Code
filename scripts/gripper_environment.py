import numpy as np
#import dynamixel_sdk as dxl

from Gripper import Gripper
from Camera import Camera
from cares_lib.vision.ArucoDetector import ArucoDetector

class Environment():
    def __init__(self):
        self.gripper = Gripper()
        self.camera = Camera()
        self.aruco_detector = ArucoDetector(marker_size=18)
        self.target_angle = self.choose_target_angle()

        self.gripper.setup()

    def reset(self):
        state, terminated = self.gripper.home()

        marker_pose = self.get_marker_pose(marker_id=0)
        #beths bad addition -- NOTE henry we may need to think of a better way to do this bc i have gotten a lot of 'NoneType' object is not subscriptable errors trying to get this to work
        if marker_pose is None:
            marker_yaw = -1
        else:
            marker_yaw = marker_pose[1][2]
        state.append(marker_yaw)

        self.target_angle = self.choose_target_angle()

        return state, terminated

    def choose_target_angle(self):
        # davids suggestion - choose 1 of 4 angles to make training easier
        target_angle = np.random.randint(1,5)
        if target_angle == 1:
            return 90
        elif target_angle == 2:
            return 180
        elif target_angle == 3:
            return 270
        elif target_angle == 4:
            return 0
        return -1 # Should not return -1

    def reward_function(self, target_angle, start_marker_pose, final_marker_pose, gripper_error):

        if final_marker_pose is None:
            print("Final Marker Pose is None")
            return 0, True
        if start_marker_pose is None: 
            print("Start Marker Pose is None")
            return 0, True

        terminated = False
        
        #NOTE to henry: this is another bad fix im not sure what u want to do with the Nones, tad confused about that so this is a work around to get the logic working :) 

        valve_angle_before = start_marker_pose[1][2]
        valve_angle_after  = final_marker_pose[1][2]

        angle_difference = np.abs(target_angle - valve_angle_after)
        # change in difference = difference - new difference
        delta_changes    = np.abs(target_angle - valve_angle_before) - np.abs(target_angle - valve_angle_after)

        reward = 0
        # maybe paramatise the noise parameters
        if -3 <= delta_changes <= 3:
            reward = 0
        else:
            reward = delta_changes

        if angle_difference <= 3:
            reward = reward + 100
            print("Reached the Goal Angle!")
            terminated = True
        
        return reward, terminated

    #TODO push this back into aruco detector at some point
    def get_marker_pose(self, marker_id):

        marker_poses = {}
        detect_attempts = 0

        while len(marker_poses) == 0 and detect_attempts < 4:
            print("detecting......")
            frame = self.camera.get_frame()
            marker_poses = self.aruco_detector.get_marker_poses(frame, self.camera.camera_matrix, self.camera.camera_distortion)
            detect_attempts += 1
        #marker_pose = None #kept between 0-360 degrees thus -1 is not found
        if marker_id in marker_poses:
            marker_pose = marker_poses[marker_id]
        else:
            marker_pose = None
        return marker_pose

    #TODO: change the 0 in all the marker pose indexing to an aruco id variable
    def step(self, action):
        
        # Get initial pose of the marker before moving to help calculate reward after moving
        start_marker_pose = self.get_marker_pose(marker_id=0)
        
        state, gripper_error = self.gripper.move(action=action)

        final_marker_pose = self.get_marker_pose(marker_id=0)
        
        final_marker_yaw = -1
        if final_marker_pose is not None:
            final_marker_yaw = final_marker_pose[1][2]

        state.append(final_marker_yaw)
        
        reward, terminated = self.reward_function(self.target_angle, start_marker_pose, final_marker_pose, gripper_error)

        truncated = False #never truncate the episode but here for completion sake
        return state, reward, terminated, truncated
            
