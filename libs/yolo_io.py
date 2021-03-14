#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import os
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
from libs.constants import DEFAULT_ENCODING
import math

TXT_EXT = '.txt'
ENCODE_METHOD = DEFAULT_ENCODING

class YOLOWriter:

    def __init__(self, foldername, filename, imgSize, databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def addBndBox(self, points, name, difficult):
        print(points)
        print(type(points))
        bndbox = {'points': points}
        bndbox['name'] = name
        bndbox['difficult'] = difficult
        self.boxlist.append(bndbox)

    def BndBox2YoloLine(self, box, classList=[], rotationAware=False):
        print(rotationAware)
        points = box['points']
        print(points)
        print(type(points))
        print(points[0])
        print(type(points[0]))
        cen = ((points[0] + points[2])[0] / 2, (points[0] + points[2])[1] / 2)
        print(cen)
        xcen = float(cen[0]) / 2 / self.imgSize[1]
        ycen = float(cen[1]) / 2 / self.imgSize[0]

        whx1 = points[0][0] - points[1][0]
        whx2 = points[0][0] - points[3][0]
        why1 = points[0][1] - points[1][1]
        why2 = points[0][1] - points[3][1]

        wh1 = math.sqrt((whx1 * whx1) + (why1 * why1))
        wh2 = math.sqrt((whx2 * whx2) + (why2 * why2))

        w = float(min(wh1, wh2)) / self.imgSize[1]
        h = float(max(wh1, wh2)) / self.imgSize[0]
        print(w)
        print(h)
        # PR387
        boxName = box['name']
        if boxName not in classList:
            classList.append(boxName)

        classIndex = classList.index(boxName)
        if rotationAware:
            p1 = points[0]
            p2 = points[1] if wh1 > wh2 else points[3]

            xDiff = p2[0] - p1[0]
            yDiff = p2[1] - p1[1]
            a = math.degrees(math.atan2(yDiff, xDiff))
            if a >= 180:
                a -= 180
            a = 90 - a

            print(classIndex, xcen, ycen, w, h)
            return classIndex, xcen, ycen, w, h ,a
        else:
            print(classIndex, xcen, ycen, w, h)
            return classIndex, xcen, ycen, w, h

    def save(self, classList=[], targetFile=None, rotationAware=False):
        print("save")
        print(rotationAware)
        out_file = None #Update yolo .txt
        out_class_file = None   #Update class list .txt

        if targetFile is None:
            out_file = open(
            self.filename + TXT_EXT, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(self.filename)), "classes.txt")
            out_class_file = open(classesFile, 'w')

        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(targetFile)), "classes.txt")
            out_class_file = open(classesFile, 'w')


        for box in self.boxlist:
            if rotationAware:
                classIndex, xcen, ycen, w, h, a = self.BndBox2YoloLine(box, classList, rotationAware)
                print (classIndex, xcen, ycen, w, h, a)
                out_file.write("%d %.6f %.6f %.6f %.6f %d\n" % (classIndex, xcen, ycen, w, h, a))
            else:
                classIndex, xcen, ycen, w, h = self.BndBox2YoloLine(box, classList, rotationAware)
                print (classIndex, xcen, ycen, w, h)
                out_file.write("%d %.6f %.6f %.6f %.6f\n" % (classIndex, xcen, ycen, w, h))

        # print (classList)
        # print (out_class_file)
        for c in classList:
            out_class_file.write(c+'\n')

        out_class_file.close()
        out_file.close()



class YoloReader:

    def __init__(self, filepath, image, classListPath=None):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.filepath = filepath

        if classListPath is None:
            dir_path = os.path.dirname(os.path.realpath(self.filepath))
            self.classListPath = os.path.join(dir_path, "classes.txt")
        else:
            self.classListPath = classListPath

        # print (filepath, self.classListPath)

        classesFile = open(self.classListPath, 'r')
        self.classes = classesFile.read().strip('\n').split('\n')

        # print (self.classes)

        imgSize = [image.height(), image.width(),
                      1 if image.isGrayscale() else 3]

        self.imgSize = imgSize

        self.verified = False
        # try:
        self.parseYoloFormat()
        # except:
            # pass

    def getShapes(self):
        return self.shapes

    def addShape(self, label, points, difficult):
        self.shapes.append((label, points, None, None, difficult))

    def rotate(self, point, sin, cos, xcen, ycen):
        x_rot = (point[0] * cos + point[1] * sin) + xcen
        y_rot = (-point[0] * sin + point[1] * cos) + ycen

        return (x_rot, y_rot)

    def yoloLine2Shape(self, classIndex, xcen, ycen, w, h, a):
        label = self.classes[int(classIndex)]

        xmin = max(- float(w) / 2, -1)
        xmax = min(float(w) / 2, 1)
        ymin = max(- float(h) / 2, -1)
        ymax = min(float(h) / 2, 1)

        xmin = int(self.imgSize[1] * xmin)
        xmax = int(self.imgSize[1] * xmax)
        ymin = int(self.imgSize[0] * ymin)
        ymax = int(self.imgSize[0] * ymax)

        p1 = (xmin, ymin)
        p2 = (xmax, ymin)
        p3 = (xmax, ymax)
        p4 = (xmin, ymax)

        xcen_img = int(self.imgSize[1] * xcen)
        ycen_img = int(self.imgSize[0] * ycen)

        s = float(math.sin(math.radians(a)))
        c = float(math.cos(math.radians(a)))
        p1 = self.rotate(p1, s, c, xcen_img, ycen_img)
        p2 = self.rotate(p2, s, c, xcen_img, ycen_img)
        p3 = self.rotate(p3, s, c, xcen_img, ycen_img)
        p4 = self.rotate(p4, s, c, xcen_img, ycen_img)
        points = [p1, p2, p3, p4]
        return label, points

    def parseYoloFormat(self):
        bndBoxFile = open(self.filepath, 'r')
        for bndBox in bndBoxFile:
            box = bndBox.strip().split(' ')
            if len(box)==5:
                classIndex, xcen, ycen, w, h, a = box
                label, points = self.yoloLine2Shape(classIndex, xcen, ycen, w, h, a)
            else:
                classIndex, xcen, ycen, w, h = bndBox.strip().split(' ')
                a = 0
                label, points = self.yoloLine2Shape(classIndex, xcen, ycen, w, h, a)

            # Caveat: difficult flag is discarded when saved as yolo format.
            self.addShape(label, points, False)
