import sys
import numpy as np
import time
import threading

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import os
import json
import math

import sys, random
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QPointF
import copy
from functools import partial

# ROOT_DIR = 'D:\\Tooth'
# ANNO_DIR = 'D:\\Tooth'
ROOT_DIR = ''
ANNO_DIR = ''
# if not os.path.exists(ANNO_DIR):
#     os.makedirs(ANNO_DIR)
PartNames = ["正面像", "正面笑像", "侧面像", "45度侧面像", "正面咬合像",
             "覆盖像", "右侧咬合像", "左侧咬合像", "上合像", "下合像"]
part_len = len(PartNames)


class Annos():
    def __init__(self):
        self.init()

    def init(self):
        self.imagepath = ''
        self.type = 0
        self.rect = []
        self.scaleratio = 1.0
        self.keypoints = []
        self.cur_keypoint = np.zeros((part_len, 3), dtype=np.float32)
        self.cur_partID = 0
        self.cur_vis = True

    def newItem(self):
        self.keypoints.append(copy.deepcopy(self.cur_keypoint.reshape(-1).tolist()))
        self.cur_keypoint = np.zeros((part_len, 3), dtype=np.float32)
        self.cur_partID = 0
        self.cur_vis = True

    def savejson(self):

        res = {'imagepath': self.imagepath, 'scaleratio': self.scaleratio, 'type': self.cur_partID+1, 'rect': self.rect}
        print(self.imagepath)
        print(self.scaleratio)
        print(self.cur_partID+1)
        print(self.rect)

        if self.imagepath != '':
            if len(self.rect) != 0:
                #开始保存json文件
                savepath = self.imagepath.replace(ROOT_DIR, ANNO_DIR) + '_annos.json'
                with open(savepath, 'w') as f:
                    json.dump(res, f)
                    print("标注信息保存成功")
            else:
                QMessageBox.question(None, '提示', "请先标注矩形", QMessageBox.Yes)
        else:
            print("Save1")
            QMessageBox.question(None, '提示', "请先加载图片", QMessageBox.Yes)

    def print(self, log):
        print('-------------- < %s > ------------' % log)
        print('imagepath:', self.imagepath)
        print('scaleratio:', self.scaleratio)
        print('keypoints:', self.keypoints)
        print('cur_keypoint:')
        print(self.cur_keypoint)
        print('cur_partID:', self.cur_partID)
        print('cur_vis:', self.cur_vis)


CurrentAnnos = Annos()
rot_angle = 0

class MyQLabel(QLabel):
    def __init__(self, parent):
        super().__init__(parent)

        self.setMouseTracking(True)

        global rot_angle
        self.label_maxw = 1200.0
        self.label_maxh = 700.0
        self.setGeometry(50, 50, self.label_maxw, self.label_maxh)

        self.pen = QPen(Qt.red)
        self.pen.setWidth(2)
        self.pen.setBrush(Qt.red)

        self.png = None

        self.first = None
        self.second = None
        self.third = None
        self.third_touying = None

        self.cnt = 0
        self.k = 0  #斜率
        self.b = 0  #与y轴的交点

    def paintEvent(self, e):
        qp = QPainter()
        qp.begin(self)
        qp.setPen(self.pen)
        #成功加载图片才画在Panel上
        if self.png:
            qp.drawPixmap(0, 0, self.png)
        if self.cnt == 1:
            #当点的数量只有一个的时候 先画一个点
            qp.drawPoint(self.first)
            #再画一条直线
            if self.second:
                qp.drawLine(self.first,self.second)
        elif self.cnt == 2:
            #当点的数量为两个的时候 先画一条线
            qp.drawLine(self.first, self.second)
            if self.third_touying:
                #根据mouseMoveEvent提供的p3投影坐标计算出p4的坐标然后将矩形补充完整 形成预览图
                qp.drawLine(self.second, self.third_touying)
                angle = math.atan( (self.second.y()-self.first.y()) / (self.second.x()-self.first.x()) )
                h = math.sqrt( ( self.second.x() - self.third_touying.x() )*( self.second.x() - self.third_touying.x() ) + (self.second.y() - self.third_touying.y()) * (self.second.y() - self.third_touying.y()) )
                if self.third_touying.y() < self.second.y():
                    p4 = QPointF(self.first.x() + h * math.sin(angle), self.first.y() - h * math.cos(angle))
                    qp.drawLine(self.third_touying, p4)
                    qp.drawLine(p4, self.first)
                else:
                    p4 = QPointF(self.first.x() - h * math.sin(angle), self.first.y() + h * math.cos(angle))
                    qp.drawLine(self.third_touying, p4)
                    qp.drawLine(p4, self.first)
        elif self.cnt == 3:
            p4 = None
            #当点数为3时 画出确定好的正方形
            qp.drawLine(self.first, self.second)
            self.k = (self.first.x()-self.second.x())/(self.second.y()-self.first.y())
            self.b = self.second.y() - self.k * self.second.x()
            self.third_touying = QPointF( (self.k*(self.third.y()-self.b)+self.third.x())/(self.k*self.k+1), self.k*(self.k*(self.third.y()-self.b)+self.third.x())/(self.k*self.k+1) + self.b  )
            qp.drawLine(self.second, self.third_touying)
            angle = math.atan((self.second.y() - self.first.y()) / (self.second.x() - self.first.x()))
            h = math.sqrt((self.second.x() - self.third_touying.x()) * (self.second.x() - self.third_touying.x()) + (self.second.y() - self.third_touying.y()) * (self.second.y() - self.third_touying.y()))
            if self.third_touying.y() < self.second.y():
                p4 = QPointF(self.first.x() + h * math.sin(angle), self.first.y() - h * math.cos(angle))
                qp.drawLine(self.third_touying, p4)
                qp.drawLine(p4, self.first)
            else:
                p4 = QPointF(self.first.x() - h * math.sin(angle), self.first.y() + h * math.cos(angle))
                qp.drawLine(self.third_touying, p4)
                qp.drawLine(p4, self.first)
            if len(CurrentAnnos.rect) >= 8:
                CurrentAnnos.rect.clear()
            #p4是左上角
            CurrentAnnos.rect.append(p4.x())
            CurrentAnnos.rect.append(p4.y())
            #p3是右上角
            CurrentAnnos.rect.append(self.third_touying.x())
            CurrentAnnos.rect.append(self.third_touying.y())
            #p1是左下角
            CurrentAnnos.rect.append(self.first.x())
            CurrentAnnos.rect.append(self.first.y())
            #p2是右下角
            CurrentAnnos.rect.append(self.second.x())
            CurrentAnnos.rect.append(self.second.y())
        qp.end()

    def mousePressEvent(self, e):
        if self.cnt == 0:
            self.first = e.pos()
            self.cnt += 1
        elif self.cnt == 1:
            self.second = e.pos()
            self.cnt += 1
        elif self.cnt == 2:
            self.third = e.pos()
            self.cnt += 1
        else:
            self.first = e.pos()
            self.second = None
            self.third = None
            self.third_touying = None
            self.cnt = 1
        print('cnt: %d' % (self.cnt))
        self.update()

    def mouseMoveEvent(self,e):
        if self.cnt == 1:
            self.second = e.pos()
            self.update()
        elif self.cnt == 2:
            # print('%d' % (self.cnt))
            self.third = e.pos()
            #求出p2 p3投影点直线方程的斜率 与p1 p2点连线垂直
            self.k = (self.first.x()-self.second.x())/(self.second.y()-self.first.y())
            #跟据斜率k 和p2的点坐标求出b 用点斜式来表示直线
            self.b = self.second.y() - self.k * self.second.x()
            #求出p3的投影点p3投影
            self.third_touying = QPointF( (self.k*(self.third.y()-self.b)+self.third.x())/(self.k*self.k+1), self.k*(self.k*(self.third.y()-self.b)+self.third.x())/(self.k*self.k+1) + self.b  )
            self.update()

    def loadimg(self, filename):
        print(filename)
        png = QPixmap(filename)
        ratio = min(self.label_maxw / png.width(), self.label_maxh / png.height())
        self.png = png.scaled(png.width() * ratio, png.height() * ratio)
        self.update()

        global CurrentAnnos
        CurrentAnnos.init()
        CurrentAnnos.imagepath = filename
        CurrentAnnos.scaleratio = ratio


class ControlWindow(QMainWindow):
    def __init__(self):

        super(ControlWindow, self).__init__()

        # 设置窗口的位置和大小
        self.setGeometry(50, 50, 1400, 800)
        # 设置窗口的标题
        self.setWindowTitle("AnnoSystem")

        #SetPath
        self.setPathAction = QAction("&SetPath", self)
        self.setPathAction.triggered.connect(self.setPath)

        #NextImage
        self.nextImageAction = QAction("&NextImage", self)
        self.nextImageAction.setShortcut("Q")
        self.nextImageAction.triggered.connect(partial(self.nextImage, +1))

        #PreImage
        self.preImageAction = QAction("&PreImage", self)
        self.preImageAction.setShortcut("A")
        self.preImageAction.triggered.connect(partial(self.nextImage, -1))

        #SaveAnno
        self.saveAction = QAction("&SaveAnno", self)
        self.saveAction.setShortcut("S")
        self.saveAction.triggered.connect(self.saveAnno)

        #NextItem
        self.nextItemAction = QAction("&NextItem", self)
        self.nextItemAction.setShortcut("R")
        self.nextItemAction.triggered.connect(self.nextItem)

        #NextPart
        self.nextPartAction = QAction("&NextPart", self)
        self.nextPartAction.setShortcut("W")
        self.nextPartAction.triggered.connect(self.nextPart)

        #+1度
        self.add1DegreeAction = QAction("&+1度", self)
        self.add1DegreeAction.setShortcut("ESC")
        self.add1DegreeAction.triggered.connect(self.Add1Degree)

        #创建菜单
        self.mainMenu = self.menuBar()
        self.mainMenu.addAction(self.setPathAction)
        self.mainMenu.addAction(self.nextImageAction)
        self.mainMenu.addAction(self.preImageAction)
        self.mainMenu.addAction(self.saveAction)
        self.mainMenu.addAction(self.nextPartAction)
        self.mainMenu.addAction(self.add1DegreeAction)

        self.qlabel = MyQLabel(self)

        BodyPartBox = QWidget(self)
        BodyPartBoxlayout = QVBoxLayout()
        self.buttonlist = []
        for i in range(part_len):
            button = QRadioButton(PartNames[i])
            button.clicked.connect(partial(self.changePart, i))
            self.buttonlist.append(button)
            BodyPartBoxlayout.addWidget(button)

        self.buttonlist[0].setChecked(True)
        self.buttonlist[0].setStyleSheet("background-color: red")
        BodyPartBox.setLayout(BodyPartBoxlayout)
        # setGeometry()方法中是个参数的函数是：
        # setGeometry(左右， 上下， 宽， 高)
        BodyPartBox.setGeometry(1270, 50, 500, 600)

        self.hintbox = QLabel(self)
        self.hintbox.setGeometry(10, 10, 1000, 50)
        self.hintbox.setText('下一张／上一张图： Q／A           下一个部位：W          保存标注结果：S           ')#旋转角度：
        #self.lineEdit = QLineEdit(self)
        # self.lineEdit.setGeometry(580, 25, 50, 20)
        # self.lineEdit.returnPressed.connect(self.lineEdit_function)

    def lineEdit_function(self):
        #先判断输入的角度是否正确
        print('PRESS: %d' % ( int(self.lineEdit.text()) ))
        global rot_angle
        rot_angle = int(self.lineEdit.text())
        self.lineEdit.clearFocus()
        self.qlabel.update()

    def setPath(self):
        get_directory_path = QFileDialog.getExistingDirectory(self, "选取指定文件夹", "D:/")
        global ROOT_DIR
        global ANNO_DIR
        ROOT_DIR = str(get_directory_path)
        ANNO_DIR = str(get_directory_path)
        self.currentID = -1
        self.imagelist = os.listdir(ROOT_DIR)
        self.imagelist = [item for item in self.imagelist if item[-4:] == '.jpg']

    def nextImage(self, direction):
        global ROOT_DIR
        global ANNO_DIR
        global CurrentAnnos
        #1.先判断有没有加载路径
        if ROOT_DIR == '' :
            QMessageBox.question(self, '提示', "请先加载路径（SetPath）", QMessageBox.Yes)
            print("请先加载路径")
            return

        #2.判断该路径下有没有.jpg
        if len(self.imagelist) == 0 :
            QMessageBox.question(self, '提示', "路径下没有jpg图片，请重新选择路径。", QMessageBox.Yes)
            print("路径下没有jpg图片")
            return

        self.currentID += direction
        self.currentID = min(max(self.currentID, 0), len(self.imagelist) - 1)
        self.currentPath = '%s/%s' % (ROOT_DIR, self.imagelist[self.currentID])
        self.qlabel.loadimg(self.currentPath)

        self.buttonlist[CurrentAnnos.cur_partID].setChecked(True)
        for bt in self.buttonlist:
            bt.setStyleSheet("background-color: None")
        self.buttonlist[CurrentAnnos.cur_partID].setStyleSheet("background-color: red")

    def saveAnno(self):
        global CurrentAnnos
        CurrentAnnos.savejson()
        self.qlabel.cnt = 0
        self.qlabel.first = None
        self.qlabel.second = None
        self.qlabel.third_touying = None
        self.qlabel.update()

    def nextPart(self):
        global CurrentAnnos
        CurrentAnnos.cur_partID += 1
        CurrentAnnos.cur_partID = CurrentAnnos.cur_partID % part_len
        CurrentAnnos.cur_vis = True
        self.buttonlist[CurrentAnnos.cur_partID].setChecked(True)
        for bt in self.buttonlist:
            bt.setStyleSheet("background-color: None")
        self.buttonlist[CurrentAnnos.cur_partID].setStyleSheet("background-color: red")

    def nextItem(self):
        global CurrentAnnos
        CurrentAnnos.newItem()
        self.buttonlist[CurrentAnnos.cur_partID].setChecked(True)
        for bt in self.buttonlist:
            bt.setStyleSheet("background-color: None")
        self.buttonlist[CurrentAnnos.cur_partID].setStyleSheet("background-color: red")
        CurrentAnnos.print('nextItem')

    def changePart(self, id):
        global CurrentAnnos
        CurrentAnnos.cur_partID = id
        CurrentAnnos.cur_vis = True
        self.buttonlist[CurrentAnnos.cur_partID].setChecked(True)
        for bt in self.buttonlist:
            bt.setStyleSheet("background-color: None")
        self.buttonlist[CurrentAnnos.cur_partID].setStyleSheet("background-color: red")
        CurrentAnnos.print('changePart')

    def Add1Degree(self):
        print('cnt before: %d'%(self.qlabel.cnt))
        self.qlabel.cnt -= 1
        print('cnt after : %d'%(self.qlabel.cnt))
        self.qlabel.update()





if __name__ == '__main__':
    # 每一pyqt5应用程序必须创建一个应用程序对象。sys.argv参数是一个列表，从命令行输入参数。
    app = QApplication(sys.argv)

    window = ControlWindow()



    # window.showMaximized()
    # 显示在屏幕上
    window.show()
    # 系统exit()方法确保应用程序干净的退出
    # 的exec_()方法有下划线。因为执行是一个Python关键词。因此，exec_()代替
    sys.exit(app.exec_())


