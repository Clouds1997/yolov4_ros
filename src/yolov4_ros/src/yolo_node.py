#!/usr/bin/python3
import sys
import os
import platform
import getpass
from unicodedata import name
import rospy
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge, CvBridgeError
import yolo_detect



class App:
    def __init__(self,net, _enable_floating_window, _enable_rate_info):
        rospy.init_node('yolo_detector', log_level=rospy.INFO)
        self.bridge = CvBridge()
        self.detector = net
        self.enable_rate_info = _enable_rate_info
        self.enable_floating_window = _enable_floating_window
        self.pre_time = rospy.Time.now()
        self.pre_rate = 0.0
        self.r = rospy.Rate(10)


    def _add_pub(self):
        self.pub_image_detected = rospy.Publisher("/image/detected", Image, queue_size=5)

    def _add_sub(self):
        rospy.Subscriber("/d400/color/image_raw", Image, self._cb_image, queue_size=1)

    def run(self):
        self._add_pub()
        self._add_sub()
        rospy.spin()

    def _cb_image(self, image):
        # rospy.loginfo("[image-light-detector] input image size: [{}, {}]".format(image.width, image.height))
        try:
            cv_image = self.bridge.imgmsg_to_cv2(image)
        except CvBridgeError as e:
            rospy.logwarn("Cannot convert ros image to cv image, err: {}".format(e))
            return
        cv_image = self.detector.realtime_detect(cv_image)
        if self.enable_rate_info:
            time_now = rospy.Time.now()
            time_interval = (time_now - self.pre_time).to_sec()
            if time_interval > 0:
                rate = 1.0 / time_interval
                rate = (rate + self.pre_rate) / 2.0
            else:
                rate = 0.0
            self.pre_rate = rate
            cv2.putText(cv_image, "FPS {:.2f}".format(rate), (0, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        if self.enable_floating_window:
            cv2.imshow('image-detected', cv_image)
        
        ros_image = self.bridge.cv2_to_imgmsg(cv_image)
        ros_image.header.frame_id = "camera/front"
        ros_image.header.stamp = rospy.Time.now()
        # rospy.loginfo("[image-light-detector] out image size: [{}, {}]".format(ros_image.width, ros_image.height))
        self.pub_image_detected.publish(ros_image)
        self.pre_time = rospy.Time.now()
        self.r.sleep()

    def _on_shutdown(self):
        if self.enable_floating_window:
            cv2.destroyAllWindows()

    def shutdown(self):
        self._on_shutdown()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._on_shutdown()
        return exc_type, exc_val, exc_tb

if __name__ == "__main__":
    enable_floating_window = rospy.get_param("~enable_floating_window", default=False)
    enable_rate_info = rospy.get_param("~enable_rate_info", default=True)
    sub_image_topic = rospy.get_param("~input_image_topic", default="/d400/color/image_raw")
    cfgfile = rospy.get_param("~model_file", default="/home/autoware/shared_dir/workspace/yolo_ws/src/yolov4_ros/models/yolov4.cfg")
    weightfile = rospy.get_param("~prototxt_file", default="/home/autoware/shared_dir/workspace/yolo_ws/src/yolov4_ros/models/yolov4.weights")
    namesfile = rospy.get_param("~namesfile", default="/home/autoware/shared_dir/workspace/yolo_ws/src/yolov4_ros/data/coco.names")
    use_cuda = rospy.get_param("~use_cuda", default=True)

    model = yolo_detect.Detector(cfgfile,weightfile,namesfile,use_cuda)

    app = App(model,enable_floating_window,enable_rate_info)
    app.run()
    