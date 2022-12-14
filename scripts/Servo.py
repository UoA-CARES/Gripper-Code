import dynamixel_sdk as dxl         # Uses Dynamixel SDK library

"""
The servo class contains methods used to change attributes of the servo motors
most useful for setting up the servos to move when they are chained togerther
Beth Cutler
"""

class Servo(object):
    addresses = {
        "torque_enable": 24,
        "torque_limit": 35,
        "led": 25,
        "goal_position": 30,
        "present_position": 37,
        "present_velocity": 38,
        "moving_speed": 32,
        "moving": 49
    }

    def __init__(self, port_handler, packet_handler, LED_colour, motor_id, torque_limit, speed_limit, max, min):
        self.port_handler = port_handler
        self.packet_handler = packet_handler

        self.LED_colour = LED_colour
        self.motor_id = motor_id

        self.torque_limit = torque_limit
        self.speed_limit = speed_limit

        self.max = max
        self.min = min

    #turn on L
    def turn_on_LED(self):
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(self.port_handler, self.motor_id, Servo.addresses["led"], self.LED_colour)
        self.process_result(dxl_comm_result, dxl_error, message="successfully turned on LEDs")

    # limit the torque of the motors
    def limit_torque(self):
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(self.port_handler, self.motor_id, Servo.addresses["torque_limit"], self.torque_limit)
        self.process_result(dxl_comm_result, dxl_error, message="has been successfully torque limited")

    # enable the torque of the motors
    def enable_torque(self):
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(self.port_handler, self.motor_id, Servo.addresses["torque_enable"], 1)
        self.process_result(dxl_comm_result, dxl_error, message="has been successfully torque enabled")

    # disable the torque of the motors
    def disable_torque(self):
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(self.port_handler, self.motor_id, Servo.addresses["torque_enable"], 0)
        self.process_result(dxl_comm_result, dxl_error, message="has successfully disabled torque" )

    # limit the speed of the servos
    def limit_speed(self):
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(self.port_handler, self.motor_id, Servo.addresses["moving_speed"], self.speed_limit)
        self.process_result(dxl_comm_result, dxl_error, message="has been successfully speed limited")

    # check whether the servo is moving using the inbuilt moving flag
    def moving_check(self):
        dxl_moving_result = self.packet_handler.read1ByteTxRx(
            self.port_handler, self.motor_id, Servo.addresses["moving"])
        return int(dxl_moving_result[0])

    # get the present position of the servo
    def present_position(self):
        # write and read to servos in order to get the present position
        dxl_comm_result = self.packet_handler.read2ByteTxRx(
            self.port_handler, self.motor_id, Servo.addresses["present_position"])
      
        return dxl_comm_result

    #return whether an action is valid or not (boolean)
    def verify_step(self, step):
        return self.min <= step <= self.max

    def process_result(self, dxl_com_result, dxl_error, message="success"):
        if dxl_com_result != dxl.COMM_SUCCESS:
            print(f"{self.packet_handler.getTxRxResult(dxl_com_result)}")
        elif dxl_error != 0:
            print(f"{self.packet_handler.getRxPacketError(dxl_error)}")
        else:
            print(f"Dynamixel#{self.motor_id} {message}")