# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ComplexGmlInfo
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
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QTimer, QDir
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QTreeWidgetItem
from qgis.PyQt.QtGui import QIcon, QColor
# Initialize Qt resources from file resources.py
# Import the code for the dialog
from .gmlinfo_dialog import ComplexGmlInfoDialog
import os
import os.path

from .pygml import pygml, util
from collections import OrderedDict
import logging

from .selectTool import SelectTool


class ComplexGmlInfo:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # Register icon search paths robustly
        self.icons_dir = None

        try:
            # Normalize + trailing slash for Qt
            norm = os.path.abspath(self.plugin_dir)
            if os.path.isdir(norm):
                self.icons_dir = norm
                QtCore.QDir.addSearchPath("plugins", self.icons_dir + os.sep)
                logging.error(f"[ComplexGmlInfo] Registered icon search path: {self.icons_dir}")

        except Exception as e:
            logging.error(f"[ComplexGmlInfo] Error probing icon dir {self.plugin_dir}: {e}")

        if not self.icons_dir:
            logging.error("[ComplexGmlInfo] No valid icon directory found! Checked: " + " | ".join(candidates))

        # initialize locale
        locale = str(QSettings().value('locale/userLocale'))[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ComplexGmlInfo_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = ComplexGmlInfoDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Complex GML Info')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'ComplexGmlInfo')
        self.toolbar.setObjectName(u'ComplexGmlInfo')

        logformat = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logfile = util.getTempfile('gmlinfo.log')
        logging.basicConfig(filename=logfile, level=logging.ERROR, format=logformat)

        self.cache = {}

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ComplexGmlInfo', message)

    def get_icon(self, name="icon.png"):
        """
        Loads an icon with fallbacks and debug logging.
        Sequence:
          1) Alias: QIcon("plugins:name")
          2) Absolute path: <self.icons_dir>/name
          3) Legacy resource: ":/plugins/ComplexGmlInfo/name"
        """
        # 1) Alias
        ico = QIcon(f"plugins:{name}")
        if not ico.isNull():
            return ico

        # 2) Absolute path
        if self.icons_dir:
            fs_path = os.path.join(self.icons_dir, name)
            if os.path.exists(fs_path):
                ico2 = QIcon(fs_path)
                if not ico2.isNull():
                    logging.error(f"[ComplexGmlInfo] Loaded icon via FS path: {fs_path}")
                    return ico2
                else:
                    logging.error(f"[ComplexGmlInfo] Icon unreadable (FS): {fs_path}")
            else:
                logging.error(f"[ComplexGmlInfo] Icon not found (FS): {fs_path}")
        else:
            logging.error("[ComplexGmlInfo] self.icons_dir is None")

        # 3) Legacy (if resources still exist)
        legacy = f":/plugins/ComplexGmlInfo/{name}"
        ico3 = QIcon(legacy)
        if not ico3.isNull():
            logging.error(f"[ComplexGmlInfo] Loaded icon via legacy resource: {legacy}")
            return ico3

        # Show diagnosis
        try:
            paths = QtCore.QDir.searchPaths("plugins")
        except Exception:
            paths = []
        QMessageBox.warning(
            self.iface.mainWindow(),
            "ComplexGmlInfo – Icon missing",
            "Could not load icon:\n"
            f"  Name: {name}\n"
            f"  searchPaths('plugins'): {paths}\n"
            f"  icons_dir: {self.icons_dir or 'None'}\n"
            f"  Legacy: {legacy}\n\n"
            "Please check: Folder/filename exists?"
        )
        logging.error(f"[ComplexGmlInfo] FAILED to load icon '{name}'. SearchPaths={paths} icons_dir={self.icons_dir}")
        return QIcon()

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = icon_path if isinstance(icon_path, QIcon) else QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon = self.get_icon("icon.png")
        self.add_action(
            icon,
            text=self.tr(u'Complex GML Info'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.add_action(
            None,
            text='About',
            callback=self.about,
            add_to_toolbar=None,
            parent=None)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Complex GML Info'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def about(self):
        infoString = "<table><tr><td colspan=\"3\"><b>Complex GML Info 0.5</b></td></tr><tr><td colspan=\"3\"></td></tr><tr><td rowspan=\"3\">Authors:</td><td>J&uuml;rgen Weichand</td><td><a href=\"mailto:juergen@weichand.de\">juergen@weichand.de</a></td></tr><tr><td colspan=\"2\">Tim Vinving</td></tr><tr><td rowspan=\"3\">Authors:</td><td>Edward Nash</td><td><a href=\"mailto:e.nash@dvz-mv.de\">e.nash@dvz-mv.de</a></td></tr><tr><td>Website:</td><td><a href=\"http://github.com/qgisinspiretools/qgis-complex-gmlinfo-plugin\">http://github.com/qgisinspiretools/qgis-complex-gmlinfo-plugin</a></td></tr></table>"
        QMessageBox.information(self.iface.mainWindow(), "About Complex GML Info", infoString)

    def run(self):
        self.dlg.treeWidget.setHeaderHidden(True)
        self.displayFeatureInfo()
        self.dlg.lineEdit.textChanged.connect(self.resetTimer)
        self.q = self.dlg.lineEdit.text()
        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.start()
        self.timer.timeout.connect(self.checkUpdateFeatureInfo)

    def resetTimer(self):
        self.timer.stop()
        self.timer.start()

    def checkUpdateFeatureInfo(self):
        if not self.q == self.dlg.lineEdit.text():
            self.q = self.dlg.lineEdit.text()
            self.updateFeatureInfo()
            self.timer.stop()
            self.timer.start()

    def displayFeatureInfo(self):
        layer = self.iface.activeLayer()

        # layer must be activated
        if not layer:
            QMessageBox.critical(self.dlg, 'Error', u'Please activate a GML layer - no layer is active!')
            return

        # layer must be GML
        if not (hasattr(layer, 'storageType') and (layer.storageType() == 'GML' or layer.storageType() == 'NAS')):
            QMessageBox.critical(self.dlg, 'Error', u'Please activate a GML layer - the active layer is not GML!')
            return

        self.previous_map_tool = self.iface.mapCanvas().mapTool()

        if not layer.selectedFeatures():
            tool = SelectTool(self.iface, self.show_Info)
            self.iface.mapCanvas().setMapTool(tool)
        else:
            self.show_Info()

    def show_Info(self):
        layer = self.iface.activeLayer()

        filename = layer.dataProvider().dataSourceUri().split('|')[0]

        if not filename in self.cache:
            logging.debug('%s not cached yet!' % filename)
            try:
                self.cache[filename] = pygml.Dataset(filename)
            except pygml.GmlException as e:
                QMessageBox.critical(self.dlg, 'Error', e.message)
                return

        gml = self.cache[filename]

        # >= 1 feature must be selected
        if not layer.selectedFeatures():
            QMessageBox.critical(self.dlg, 'Error', u'Please select one or more feature(s) first!')
            return
        else:
            self.dlg.show()

        features = OrderedDict()
        i = 0

        for feature in layer.selectedFeatures():
            if feature.attribute('gml_id'):
                i+=1
                gml_id = feature.attribute('gml_id')
                features['Selected feature [' + str(i) +']'] = gml.getFeature(gml_id)

        self.fill_widget(self.dlg.treeWidget, features)

        if self.previous_map_tool:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)

    # based on http://stackoverflow.com/questions/21805047/qtreewidget-to-mirror-python-dictionary
    def fill_item(self, item, value):
        item.setExpanded(True)
        if type(value) is OrderedDict:
            for key, val in sorted(value.items()):
                if type(val) is str:
                    if '@xmlns' not in key: # hack
                        child = QTreeWidgetItem()
                        text = str(key + " '" + val + "'")
                        child.setForeground(0, self.getQColor(text))
                        child.setText(0, text)
                        item.addChild(child)
                else:
                    child = QTreeWidgetItem()
                    text = str(key)
                    #child.setForeground(0, self.getQColor(text))
                    child.setText(0, text)
                    item.addChild(child)
                    self.fill_item(child, val)
        elif type(value) is list:
            for val in value:
                child = QTreeWidgetItem()
                item.addChild(child)
                if type(val) is OrderedDict:
                    child.setText(0, '[' + str(value.index(val)) +']')
                    self.fill_item(child, val)
                elif type(val) is list:
                    child.setText(0, '[' + str(value.index(val)) +']')
                    self.fill_item(child, val)
                else:
                    child.setText(0, str(val))
                    child.setExpanded(True)
        else:
            child = QTreeWidgetItem()
            child.setText(0, str(value))
            item.addChild(child)

    def fill_widget(self, widget, value):
        widget.clear()
        self.fill_item(widget.invisibleRootItem(), value)

    # colorize attributes
    def getQColor(self, text):
        for indicator in ['nil']:
            if indicator in text.lower():
                return QColor('lightgrey')
        for indicator in ['gml:id', 'localid', 'identifier', 'xlink:href', 'xlink:type', 'namespace', 'codespace']:
            if indicator in text.lower():
                return QColor(244,134,66)
        return QColor('green')

    # search inside QTreeWidget
    def updateFeatureInfo(self):
        self.displayFeatureInfo()
        query = str(self.dlg.lineEdit.text())
        if query and len(query) >= 3:
            root_item = self.dlg.treeWidget.invisibleRootItem()
            self.removeChildren(root_item, query)

    def removeChildren(self, item, query):
        if item:
            child_count = item.childCount()
            if child_count > 0:
                for i in range(child_count):
                    self.removeChildren(item.child(i), query)

            else:
                path = self.buildPath(item)
                if not query.lower() in self.buildPath(item).lower():
                    parent = item.parent()
                    if parent:
                        parent.removeChild(item)
                        self.removeChildren(parent, query)

    def buildPath(self, item):
        text = item.text(0)
        if item.parent():
            text += ' > ' + self.buildPath(item.parent())
        return text
