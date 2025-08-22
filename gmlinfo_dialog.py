# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ComplexGmlInfoDialog
                                 A QGIS plugin
 Display feature info of complex feature types.
                             -------------------
        begin                : 2015-09-16
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Juergen Weichand
        email                : juergen@weichand.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import *
from qgis.PyQt import QtWidgets, uic


UI_PATH = os.path.join(os.path.dirname(__file__), 'gmlinfo_dialog_base.ui')

class ComplexGmlInfoDialog(QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        uic.loadUi(UI_PATH, self)
