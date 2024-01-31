#!/usr/bin/env python3

import rospy
import time
import math
from std_msgs.msg import Header, String
import numpy as np
import cv2
from apriltag import apriltag
from PIL import Image as im
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped, Point, Pose, Quaternion, TransformStamped, Vector3, Transform
import time
from tf.transformations import quaternion_from_euler, quaternion_from_matrix
import tf
from pyquaternion import Quaternion as pyQuaternion
from std_msgs.msg import Float32
import cv2
import statistics


def object_points(tag_size):
    return [[-tag_size / 2, tag_size / 2, 0.0],
            [tag_size / 2, tag_size / 2, 0.0],
            [tag_size / 2, -tag_size / 2, 0.0],
            [-tag_size / 2, -tag_size / 2, 0.0]]

class Image_Processing:
    def __init__(self):

        self.tag_size = 0.079  # tag size in meters
        fx_green= 1357.7098
        fy_green = 1364.4257
        cx_green = 951.6751
        cy_green = 511.0647


        self.cam1_intrinsics = np.array([[fx_green, 0, cx_green],
                                         [0, fy_green, cy_green],
                                         [0, 0, 1]])
        self.cam2_intrinsics = np.zeros((3, 3))
        self.br = tf.TransformBroadcaster()
        self.cam1_rot = np.zeros((4, 4))
        self.cam2_rot = np.zeros((4, 4))


    def pipeline(self, image, in_init, imageName):

        intrinsics_mat = self.cam1_intrinsics
        '''if camera == 'cam1':
            intrinsics_mat = self.cam1_intrinsics
        else:
            intrinsics_mat = self.cam2_intrinsics
        '''

        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if in_init:
            self.tag_size = 0.079
        else:
            self.tag_size = 0.025
        obj_pts = np.array(object_points(self.tag_size))
        detector = apriltag(family="tag36h11")
        detections = detector.detect(gray_image)  # , estimate_tag_pose=True, camera_params=PARAMS, tag_size=TAG_SIZE)
        # rospy.loginfo("Detector Time " + str(time2 - time1))

        found_objects = {}

        # rospy.loginfo("showing")

        cv2.imshow(imageName, image)
        cv2.waitKey(1)

        # rospy.loginfo("finished")

        # if len(detections) > 0:
        #     rospy.loginfo(imageName + "DETECTED IMAGE");
        #     for tag in detections:
        #         center = tag['center']
        #         lb_rb_rt_lt = tag['lb-rb-rt-lt']
        #         lt_rt_rb_lb = np.zeros((4, 2))
        #         for i in range(4):
        #             lt_rt_rb_lb[i] = lb_rb_rt_lt[3 - i]

        #         good, prvecs, ptvecs = cv2.solvePnP(obj_pts, lt_rt_rb_lb, intrinsics_mat, (),
        #                                             flags=cv2.SOLVEPNP_IPPE_SQUARE)

        #         if good:

        #             # pt = lt_rt_rb_lb[0]
        #             # print(tuple(pt))

        #             # p1 = (int(lt_rt_rb_lb[0][0]), int(lt_rt_rb_lb[0][1]))
        #             # p2 = (int(lt_rt_rb_lb[1][0]), int(lt_rt_rb_lb[1][1]))
        #             # p3 = (int(lt_rt_rb_lb[2][0]), int(lt_rt_rb_lb[2][1]))
        #             # p4 = (int(lt_rt_rb_lb[3][0]), int(lt_rt_rb_lb[3][1]))
        #             #
        #             # image = cv2.line(image, p1, p2, (0, 255, 0), 2)
        #             # image = cv2.line(image, p2, p3, (0, 255, 0), 2)
        #             # #new_image = cv2.line(new_image, p3, p4, (0, 255, 0), 2)
        #             # #new_image = cv2.line(new_image, p4, p1, (0, 255, 0), 2)
        #             #
        #             # cv2.imshow(imageName, image)
        #             # cv2.waitKey(0)
        #             # time1 = self.current_milli_time()
        #             ID = tag['id']
        #             object_name = ""
        #             if in_init and ID == 47:
        #                 object_name = "tag"
        #             elif not in_init:
        #                 if ID == 0:
        #                     object_name = "grey_cube"
        #                 if ID == 1:
        #                     object_name = "corn_can"
        #                 if ID == 2:
        #                     object_name = "bottle_2"
        #             else:
        #                 continue

        #             rot_matrix, _ = cv2.Rodrigues(prvecs)
        #             mat = np.zeros((4, 4), np.float32)
        #             for i in range(3):
        #                 for j in range(3):
        #                     mat[i][j] = rot_matrix[i][j]

        #             mat[3, 3] = 1

        #             mat[0, 3] = ptvecs[0][0]
        #             mat[1, 3] = ptvecs[1][0]
        #             mat[2, 3] = ptvecs[2][0]

        #             # handle pos

        #             if in_init and ID == 47:
        #                 mat = np.linalg.inv(mat)

        #             orientation = quaternion_from_matrix(mat)

        #             translation = [mat[0, 3], mat[1, 3], mat[2, 3]]

        #             found_objects[object_name] = (translation, orientation)

        return found_objects

class Pipeline:

    def __init__(self):
        """
        Class constructor
        """
        ### Initialize node, name it 'lab2'
        rospy.init_node('pipeline')

        self.br = tf.TransformBroadcaster()

        self.pipeline_rate = 0

        self.current_image = 0
        self.intrinsics = 0
        self.plot_publisher = rospy.Publisher('/plot/value', Float32, queue_size=10)

        ### Making robot go 10Hz
        self.rate = rospy.Rate(30)
        self.count = 0

        self.br.sendTransform((0, 0, 0), tf.transformations.quaternion_from_euler(0, 0, 0), rospy.Time.now(), "adjust",
                              "world")

        self.publish_ready = rospy.Publisher('/status', String, queue_size=10)

        self.t1 = [0.0, 0.0, 0.0]
        self.q1 = [0.0, 0.0, 0.0, 0.0]

        self.t2 = [0.0, 0.0, 0.0]
        self.q2 = [0.0, 0.0, 0.0, 0.0]

        self.listener = tf.TransformListener()

        self.sample_done = False
        self.image_count = 0

        self.tagIDs = [0, 1, 2]

        self.processor = Image_Processing()

        self.median_filter = [TransformStamped(), TransformStamped(), TransformStamped()]
        self.median_count = 0
        self.still_count = 5

        self.tag_size = 0.079  # tag size in meters
        self.br = tf.TransformBroadcaster()
        self.cam1_rot = np.zeros((4, 4))
        self.cam2_rot = np.zeros((4, 4))

        self.ready = ''

        rospy.Subscriber('/status', String, self.callback)
        self.listener = tf.TransformListener()
        rospy.sleep(2)
        self.br.sendTransform((0, 0, 0), tf.transformations.quaternion_from_euler(0, 0, 0), rospy.Time.now(), "adjust",
                              "world")
        self.object_name_list = ["grey_cube", "corn_can", "bottle_2"]
        rospy.sleep(1)

    def callback(self,data):
        self.ready = data.data

    def broadcaster(self):

        while not self.sample_done:

            rospy.loginfo("Initiating Sampling")
            while self.image_count < 10:
                self.image_count = self.image_count + 1

            # cv2.imshow("Nice Camera", image1)
            # cv2.imshow("Other Camera", image2)
            cv2.waitKey(0)

            rospy.loginfo("Processing Camera 1")
            found_tag1 = self.processor.pipeline(image1, True, "4K")
            
            rospy.loginfo("Processing Camera 2")
            found_tag2 = self.processor.pipeline(image2, True, "Onlyfans")


            cam1_translation = found_tag1['tag'][0]
            cam1_rotation = found_tag1['tag'][1]

            cam2_translation = found_tag2['tag'][0]
            cam2_rotation = found_tag2['tag'][1]

            rospy.loginfo("Finishing Sampling")

            self.t1[0] = cam1_translation[0]
            self.t1[1] = cam1_translation[1]
            self.t1[2] = cam1_translation[2]

            self.q1[0] = cam1_rotation[0]
            self.q1[1] = cam1_rotation[1]
            self.q1[2] = cam1_rotation[2]
            self.q1[3] = cam1_rotation[3]

            self.t2[0] = cam2_translation[0]
            self.t2[1] = cam2_translation[1]
            self.t2[2] = cam2_translation[2]

            self.q2[0] = cam2_rotation[0]
            self.q2[1] = cam2_rotation[1]
            self.q2[2] = cam2_rotation[2]
            self.q2[3] = cam2_rotation[3]

            self.sample_done = True


        transform1 = Transform()
        transform1.translation = Vector3(self.t1[0], self.t1[1], self.t1[2])
        transform1.rotation = Quaternion(self.q1[0], self.q1[1], self.q1[2], self.q1[3])

        transform2 = Transform()
        transform2.translation = Vector3(self.t2[0], self.t2[1], self.t2[2])
        transform2.rotation = Quaternion(self.q2[0], self.q2[1], self.q2[2], self.q2[3])

        self.br.sendTransform((transform1.translation.x, transform1.translation.y, transform1.translation.z), (
            transform1.rotation.x, transform1.rotation.y, transform1.rotation.z, transform1.rotation.w),
                              rospy.Time.now(), "camera_green", "adjust_objects")

        self.br.sendTransform((transform2.translation.x, transform2.translation.y, transform2.translation.z), (
            transform2.rotation.x, transform2.rotation.y, transform2.rotation.z, transform2.rotation.w),
                              rospy.Time.now(), "camera_purple", "adjust_objects")



    def update_current_image(self, camera1, camera2):
            # Show images
            # self.broadcaster()

            ret1, image1 = camera1.read()
            ret2, image2 = camera2.read()


            # if ret1 and ret2:
            #     self.publish(image1, image2)
            #self.record_images(color_image)
            # cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
            #cv2.imshow('RealSense', images1)
            # cv2.waitKey(1)

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
        cv2.destroyAllWindows()
    
    def publish(self, image1, image2):

        self.pipeline_rate += 1
        rospy.loginfo(self.pipeline_rate)

        tags = self.processor.pipeline(image1, False, "4K")

        for object_name in self.object_name_list:
            if object_name in tags.keys():

                transform = Transform()
                translation = tags[object_name][0]
                quaternion = tags[object_name][1]

                transform.translation = Vector3(translation[0], translation[1], translation[2])
                transform.rotation = Quaternion(quaternion[0], quaternion[1], quaternion[2], quaternion[3])
                self.br.sendTransform((transform.translation.x, transform.translation.y, transform.translation.z), (transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w), rospy.Time.now(), object_name + "_green", "camera_green")

        # tags = self.processor.pipeline(image2, False, "Other Cam")
        # for object_name in self.object_name_list:
        #     if object_name in tags.keys():
        #         transform = Transform()
        #         translation = tags[object_name][0]
        #         quaternion = tags[object_name][1]

        #         transform.translation = Vector3(translation[0], translation[1], translation[2])
        #         transform.rotation = Quaternion(quaternion[0], quaternion[1], quaternion[2], quaternion[3])

        #         self.br.sendTransform((transform.translation.x, transform.translation.y, transform.translation.z), (transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w), rospy.Time.now(), object_name + "_purple", "camera_purple")


    def current_milli_time(self):
        return round(time.time() * 1000)

    def run(self):
        r = rospy.Rate(60)
        # # Start streaming
        camera1 = cv2.VideoCapture(0)
        camera2 = cv2.VideoCapture(4)

        camera1.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        camera1.set(cv2.CAP_PROP_FPS, 30)

        camera2.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        camera2.set(cv2.CAP_PROP_FPS, 30)
        camera2.set(3, 2500)
        camera2.set(4, 1900)
        while not rospy.is_shutdown():
            ret, im = camera2.read()
            if ret:
                cv2.imshow("d", im)
                cv2.waitKey(1)
            #self.update_current_image(camera1, camera2)
        
        rospy.spin()

if __name__ == '__main__':
    Pipeline().run()
