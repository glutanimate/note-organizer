# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'designer/organizer.ui'
#
# Created: Sat Apr 15 22:01:48 2017
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(906, 498)
        self.verticalLayout_2 = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.tableLayout = QtGui.QVBoxLayout()
        self.tableLayout.setSizeConstraint(QtGui.QLayout.SetFixedSize)
        self.tableLayout.setObjectName(_fromUtf8("tableLayout"))
        self.verticalLayout_2.addLayout(self.tableLayout)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.date = QtGui.QDateTimeEdit(Dialog)
        self.date.setObjectName(_fromUtf8("date"))
        self.horizontalLayout.addWidget(self.date)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.horizontalLayout.addWidget(self.buttonBox)
        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Reorganize Notes", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Start from", None, QtGui.QApplication.UnicodeUTF8))
        self.date.setDisplayFormat(QtGui.QApplication.translate("Dialog", "yyyy-MM-dd HH:mm", None, QtGui.QApplication.UnicodeUTF8))

