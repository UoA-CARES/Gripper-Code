import logging
import random
from enum import Enum
from time import sleep
import dynamixel_sdk as dxl
from functools import wraps

from serial import Serial

from configurations import ObjectConfig
from cares_lib.vision.Camera import Camera
from cares_lib.vision.ArucoDetector import ArucoDetector

from cares_lib.dynamixel.Servo import Servo


def exception_handler(error_message):
    def decorator(function):
        @wraps(function)
        def wrapper(self, *args, **kwargs):
            try:
                return function(self, *args, **kwargs)
            except EnvironmentError as error:
                logging.error(f"Environment for Gripper#{error.gripper.gripper_id}: {error_message}")
                raise EnvironmentError(error.gripper, f"Environment for Gripper#{error.gripper.gripper_id}: {error_message}") from error
        return wrapper
    return decorator


class Command(Enum):
    GET_YAW = 0
    OFFSET = 1


class ServoObject(object):
    def __init__(self, config: ObjectConfig, servo_id, model="XL330-M077-T") -> None:
        self.device_name = config.object_device_name
        self.model = model

        self.min = 0
        self.max = 4095
        self.protocol = 2
        self.baudrate = config.object_baudrate

        self.port_handler = dxl.PortHandler(self.device_name)
        self.packet_handler = dxl.PacketHandler(self.protocol)
        self.setup_handlers()
        self.servo_id = servo_id

        self.object_servo = Servo(self.port_handler, self.packet_handler, 2.0, servo_id, 0, 200, 200, self.max, self.min, self.model)

    def setup_handlers(self):
        if not self.port_handler.openPort():
            error_message = f"Failed to open port {self.device_name}"
            logging.error(error_message)
            raise IOError(error_message)
        logging.info(f"Succeeded to open port {self.device_name}")

        if not self.port_handler.setBaudRate(self.baudrate):
            error_message = f"Failed to change the baudrate to {self.baudrate}"
            logging.error(error_message)
            raise IOError(error_message)
        logging.info(f"Succeeded to change the baudrate to {self.baudrate}")

    def get_yaw(self):
        current_position = self.object_servo.current_position()
        yaw = self.object_servo.step_to_angle(current_position)
        if yaw < 0:
            yaw += 360
        return yaw

    def reset(self):
        reset_home_position = random.randint(self.min, self.max)
        self.object_servo.move(reset_home_position)
        self.object_servo.disable_torque()

    @exception_handler("Failed while trying to reset target servo")
    def reset_target_servo(self, home_pos):
        self.object_servo.enable_torque()
        logging.info(f"Resetting Servo #{self.servo_id} to position: {home_pos}")
        self.object_servo.move(home_pos)
        self.object_servo.disable_torque()


class ArucoObject(object):
    def __init__(self, camera: Camera, aruco_detector: ArucoDetector, object_marker_id: int) -> None:
        self.camera = camera
        self.aruco_detector = aruco_detector
        self.object_marker_id = object_marker_id

    def get_yaw(self, blindable=False, detection_attempts=10):
        attempt = 0
        while not blindable or attempt < detection_attempts:
            attempt += 1
            msg = f"{attempt}/{detection_attempts}" if blindable else f"{attempt}"
            logging.debug(f"Attempting to detect aruco target: {self.object_marker_id}")

            frame = self.camera.get_frame()
            marker_poses = self.aruco_detector.get_marker_poses(frame, self.camera.camera_matrix,
                                                                self.camera.camera_distortion, display=False)
            if self.object_marker_id in marker_poses:
                return marker_poses[self.object_marker_id]["orientation"][2]
        return None

    def reset(self):
        pass

    def reset_target_servo(self):
        pass


# TODO: Function may be deprecated if not returning to magnetic encoder.
class MagnetObject(object):
    def __init__(self, config: ObjectConfig, aruco_yaw=None) -> None:
        self.serial = Serial(config.device_name, config.baudrate)
        sleep(1)
        if aruco_yaw is not None:
            self.offset(aruco_yaw)

    def get_response(self):
        return self.serial.read_until(b'\n').decode().split(",")

    def get_yaw(self):
        command = f"{Command.GET_YAW.value},"
        try:
            self.serial.write(command.encode())
            response = self.get_response()

            while response[0] != "YAW":
                self.serial.write(command.encode())
                response = self.get_response()

            yaw = float(response[1])
            return yaw
        except (UnicodeDecodeError, ValueError):
            logging.info("get_yaw: Error reading from serial port, retrying...")

    def offset(self, aruco_yaw):
        logging.info("Calibrating magnet to aruco reading...")
        command = f"{Command.OFFSET.value},{aruco_yaw}\n"
        try:
            self.serial.write(command.encode())
            response = self.get_response()

            while response[0] != "OFFSET":
                self.serial.write(command.encode())
                response = self.get_response()

            success = bool(response[1])
            return success
        except (UnicodeDecodeError, ValueError):
            logging.info("Offset: Error reading from serial port, retrying...")

    def reset(self):
        pass

    def reset_target_servo(self):
        pass
