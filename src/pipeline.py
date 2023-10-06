#!/usr/bin/env python3

import rospy
import math
from std_msgs.msg import Header
import numpy as np
import cv2
from apriltag import apriltag
from PIL import Image as im
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped, Point, Pose, Quaternion, TransformStamped, Vector3, Transform
import pyrealsense2 as rs
import time
from tf.transformations import quaternion_from_euler, quaternion_from_matrix
import tf
from pyquaternion import Quaternion as pyQuaternion
from std_msgs.msg import Float32
import statistics



def object_points(tag_size):
    return [[-tag_size / 2, tag_size / 2, 0.0],
            [tag_size / 2, tag_size / 2, 0.0],
            [tag_size / 2, -tag_size / 2, 0.0],
            [-tag_size / 2, -tag_size / 2, 0.0]]


class Pipeline:

    def __init__(self):
        """
        Class constructor
        """

        ### Initialize node, name it 'lab2'
        rospy.init_node('pipeline')
        self.pipeline_rate = 0

        self.current_image = 0
        self.intrinsics = 0
        self.plot_publisher = rospy.Publisher('/plot/value', Float32, queue_size=10)
        # camera setup through pyrealsense2
        self.rspipeline = rs.pipeline()
        self.rsconfig = rs.config()

        self.rspipe_wrapper = rs.pipeline_wrapper(self.rspipeline)
        self.pipeline_profile = self.rsconfig.resolve(self.rspipe_wrapper)
        self.device = self.pipeline_profile.get_device()
        self.device_product_line = str(self.device.get_info(rs.camera_info.product_line))

        found_rgb = False
        for s in self.device.sensors:
            if s.get_info(rs.camera_info.name) == 'RGB Camera':
                found_rgb = True
                break
        if not found_rgb:
            rospy.loginfo("The demo requires Depth camera with Color sensor")
            exit(0)

        self.rsconfig.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

        self.rsconfig.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

        ### Making robot go 10Hz
        self.rate = rospy.Rate(60)
        self.count = 0

        self.initialized = False
        self.previousQuat = [0, 0, 0, 0]
        self.previousFour = [0, 0, 0, 0]
        self.prevCounter = 0
        self.inMotion = False
        self.prevTrans = 0
        self.threshold = 0.03

        # use for normal distribution
        # self.rolling_values = np.zeros(20)
        # self.rolling_index = 0
        
        # use for entropy
        self.rolling_values = []

        self.median_filter = [TransformStamped(), TransformStamped(), TransformStamped()]
        self.median_count = 0

        self.listener = tf.TransformListener()
        self.br = tf.TransformBroadcaster()
        #
        rospy.sleep(1)

    def update_current_image(self):

        # # Start streaming
        self.rspipeline.start(self.rsconfig)

        try:
            while True:

                # Wait for a coherent pair of frames: depth and color
                # lines 98 and 100 are used to test frame rate
                # self.tim = self.current_milli_time()
                frames = self.rspipeline.wait_for_frames()
                # rospy.loginfo("Cam Time: " + str(self.current_milli_time() - self.tim))
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()
                if not depth_frame or not color_frame:
                    continue

                # Convert images to numpy arrays
                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())

                # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

                depth_colormap_dim = depth_colormap.shape
                color_colormap_dim = color_image.shape

                # If depth and color resolutions are different, resize color image to match depth image for display
                if depth_colormap_dim != color_colormap_dim:
                    resized_color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]),
                                                     interpolation=cv2.INTER_AREA)
                    images = np.hstack((resized_color_image, depth_colormap))
                else:
                    images = np.hstack((color_image, depth_colormap))

                # Show images
                self.pipeline(color_image)
                #self.record_images(color_image)
                # cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
                # cv2.imshow('RealSense', images)
                # cv2.waitKey(1)
        finally:
            self.rspipeline.stop()

    def record_images(self, image):
        # height = image.height
        # width = image.width
        #
        # # Loop through each pixel of the map and convert it to pixel data
        # new_image = np.zeros((height, width, 3), dtype=np.uint8)
        #
        # for i in range(height):
        #     for j in range(width):
        #         for k in range(3):
        #             # BGR encoding for opencv
        #
        #             mult = 2 if k == 0 else 0 if k == 2 else 1
        #             cell = image.data[(i * width * 3 + j * 3 + k)]
        #             if cell >= 0:
        #                 new_image[i][j][mult] = cell
        cv2.imwrite(str(self.count) + ".jpg", image)
        print("done writing image")
        print(self.count)
        self.count += 1
        rospy.sleep(2)

    def filter_readings(self, orientation):
        
        #q = pyQuaternion(axis=[orientation[0], orientation[1], orientation[2]], angle=orientation[3])

        
        self.rolling_values.append(q)
        if len(self.rolling_values) > 10:
            self.rolling_values.pop(0)
        
        sum_x, sum_y, sum_z = 0, 0, 0
        
        for q in self.rolling_values:
            x = q[0]
            y = q[1]
            z = q[2]
            w = q[3]
            
            sum_x = sum_x + w*x
            sum_y = sum_y + w*y 
            sum_z = sum_z + w*z
        
        avg_x = sum_x / len(self.rolling_values)
        avg_y = sum_y / len(self.rolling_values)
        avg_z = sum_z / len(self.rolling_values)

        new_w = pow((pow(avg_x , 2) + pow(avg_y, 2) + pow(avg_z, 2)) , 0.5)

        new_x = avg_x / new_w
        new_y = avg_y / new_w
        new_z = avg_z / new_w



        '''
        if len(self.rolling_values) < 2:
            return orientation
        else:

            if len(self.rolling_values) > 10:
                self.rolling_values.pop(0)

            avg = []
            avg_hash = {}
            for i in range(len(self.rolling_values)):
                
                sum = 0

                for j in range(len(self.rolling_values)):
                    sum = sum + pyQuaternion.distance(self.rolling_values[i][0], self.rolling_values[j][0])

                avg.append(sum/len(self.rolling_values))
                avg_hash[i] = avg

            median = statistics.median(avg)
        
            
            sorted_avg = sorted(avg)
            index = int(len(sorted_avg) / 2)
            
            mid_points = []
            mid_points.append(rolling_values.get(index - 1))
            mid_points.append(rolling_values.get(index))
            mid_points.append(rolling_values.get(index + 1))
            

    

            for key, value in avg_hash.items():
                if value == median:if condition:
                    pass
                    index = key
                

            msg = Float32()
            msg.data = median
            self.plot_publisher.publish(msg)
            rospy.loginfo(index)

            return self.rolling_values[index][0]
        '''
    # image as image message
    def pipeline(self, image):
        # height = image.height
        # width = image.width

        # # Loop through each pixel of the map and convert it to pixel data
        # new_image = np.zeros((height, width, 3), dtype=np.uint8)

        # for i in range(height):
        #     for j in range(width):
        #         for k in range(3):
        #             # BGR encoding for opencv
        #             mult = 2 if k == 0 else 0 if k == 2 else 1
        #             cell = image.data[(i * width * 3 + j * 3 + k)]
        #             if cell >= 0:
        #                 new_image[i][j][mult] = cell

        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # rospy.loginfo("Convert Time " + str(time2 - time1))

        # cv2.imshow("header", new_image)
        # cv2.waitKey(0)

        # # closing all open windows
        # cv2.destroyAllWindows()

        # 1080 by 1920
        #   FocalLength: [1380.4628 1379.4309]
        #   PrincipalPoint: [956.5579 542.9203]
        # fx = 1380.4628
        # fy = 1379.4309
        # cx = 956.5579
        # cy = 542.9203

        # 480 by 640
        # fx = 629.0741
        # fy = 615.1736
        # cx = 325.2477
        # cy = 251.2810

        # 1280 by 720
        # FocalLength: [908.3491 906.5133]
        # PrincipalPoint: [632.3028 343.9200]
        # fx = 908.3491
        # fy = 906.5133
        # cx = 632.3028
        # cy = 343.9200
        # Camera 2
        fx = 900.1325
        fy = 900.2865
        cx = 631.4351
        cy = 342.4242

        intrinsics_mat = np.array([[fx, 0, cx],
                                   [0, fy, cy],
                                   [0, 0, 1]])  # elements from the K matrix

        TAG_SIZE = 0.025 #0.062 # Tag size from Step 1 in meters
        obj_pts = np.array(object_points(TAG_SIZE))
        detector = apriltag(family="tag36h11")
        detections = detector.detect(gray_image)  # , estimate_tag_pose=True, camera_params=PARAMS, tag_size=TAG_SIZE)
        # rospy.loginfo("Detector Time " + str(time2 - time1))
        if len(detections) > 0:
            for tag in detections:
                center = tag['center']
                lb_rb_rt_lt = tag['lb-rb-rt-lt']
                lt_rt_rb_lb = np.zeros((4, 2))
                for i in range(4):
                    lt_rt_rb_lb[i] = lb_rb_rt_lt[3 - i]

                # rospy.loginfo(lt_rt_rb_lb)

                # time1 = self.current_milli_time()
                good, prvecs, ptvecs = cv2.solvePnP(obj_pts, lt_rt_rb_lb, intrinsics_mat, (),
                                                    flags=cv2.SOLVEPNP_IPPE_SQUARE)
                # time2 = self.current_milli_time()
                # rospy.loginfo("Solver Time " + str(time2 - time1))

                if good:

                    # pt = lt_rt_rb_lb[0]
                    # print(tuple(pt))

                    # p1 = (int(lt_rt_rb_lb[0][0]), int(lt_rt_rb_lb[0][1]))
                    # p2 = (int(lt_rt_rb_lb[1][0]), int(lt_rt_rb_lb[1][1]))
                    # p3 = (int(lt_rt_rb_lb[2][0]), int(lt_rt_rb_lb[2][1]))
                    # p4 = (int(lt_rt_rb_lb[3][0]), int(lt_rt_rb_lb[3][1]))
                    #
                    # image = cv2.line(image, p1, p2, (0, 255, 0), 2)
                    # image = cv2.line(image, p2, p3, (0, 255, 0), 2)
                    # #new_image = cv2.line(new_image, p3, p4, (0, 255, 0), 2)
                    # #new_image = cv2.line(new_image, p4, p1, (0, 255, 0), 2)
                    #
                    # cv2.imshow("max range", image)
                    # cv2.waitKey(0)
                    # time1 = self.current_milli_time()


                    # Make 2 Pose w/ vectors

                    # handle rotation
                    transform = Transform()
                    transform.translation = Vector3(ptvecs[0][0], ptvecs[1][0], ptvecs[2][0])

                    rot_matrix,_ = cv2.Rodrigues(prvecs)


                    new_mat = np.zeros((4,4), np.float32)
                    for i in range(3):
                        for j in range(3):
                            new_mat[i][j] = rot_matrix[i][j]
                    new_mat[3,3] = 1
                    #rospy.loginfo(rot_matrix)
                    # handle pos
                    orientation = quaternion_from_matrix(new_mat)

                    #orientation = self.filter_readings(orientation, ptvecs)


                    transform.rotation = Quaternion(orientation[0], orientation[1], orientation[2], orientation[3])


                    self.br.sendTransform((transform.translation.x, transform.translation.y, transform.translation.z), (
                    transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w),
                                     rospy.Time.now(), "calibration_box", "camera")

                # imgpts, jac = cv2.projectPoints(opoints, prvecs, ptvecs, intrinsics_mat)
                # draw_boxes(new_image, imgpts, edges)

    def current_milli_time(self):
        return round(time.time() * 1000)

    def run(self):
        r = rospy.Rate(60)

        while not rospy.is_shutdown():
            self.update_current_image()
        rospy.spin()


if __name__ == '__main__':
    Pipeline().run()
