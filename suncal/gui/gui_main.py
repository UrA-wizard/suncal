''' Main Window for PSL Uncertainty Calculator GUI '''
import sys
from contextlib import suppress
from PyQt5 import QtWidgets, QtGui, QtCore

from .. import version
from ..project import Project, ProjectUncert, ProjectRisk, ProjectDataSet, ProjectDistExplore, ProjectReverse, \
                      ProjectSweep, ProjectReverseSweep, ProjectCurveFit, ProjectUncertWizard
from ..common import report
from . import gui_common
from . import gui_widgets
from . import configmgr
from . import page_about
from . import page_uncert
from . import page_dataset
from . import page_curvefit
from . import page_reverse
from . import page_risk
from . import page_sweep
from . import page_wizard
from . import page_distribution
from . import page_interval
from . import page_ttable
from . import page_units
from .help_strings import MainHelp


class ToolButton(QtWidgets.QToolButton):
    ''' Button for selecting project components. ToolButton with text and icon. '''
    def __init__(self, text='', icon=None, parent=None):
        super().__init__(parent=parent)
        self.setIconSize(QtCore.QSize(32, 32))
        self.setFixedSize(84, 84)
        self.setText(text)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        if icon:
            self.setIcon(icon)


class CalculationsListWidget(QtWidgets.QListWidget):
    ''' List for showing calculations in project '''
    itemRenamed = QtCore.pyqtSignal(int, str)  # Index, new text string

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # Credit for editfinished signal:
        # https://falsinsoft.blogspot.com/2013/11/qlistwidget-and-item-edit-event.html
        self.itemDelegate().closeEditor.connect(self.ListWidgetEditEnd)

    def addItem(self, mode, label):
        ''' Override addItem to automatically add an icon and make editable '''
        super().addItem(label)
        item = self.item(self.count()-1)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        iconame = {'uncertainty': 'target',
                   'wizard': 'wizard',
                   'curvefit': 'curvefit',
                   'risk': 'risk',
                   'sweep': 'targetlist',
                   'reverse': 'calipers',
                   'reversesweep': 'rulersweep',
                   'data': 'boxplot',
                   'interval': 'interval',
                   'intervaltest': 'interval',
                   'intervaltestasset': 'interval',
                   'intervalbinom': 'interval',
                   'intervalbinomasset': 'interval',
                   'intervalvariables': 'interval',
                   'intervalvariablesasset': 'interval',
                   'distributions': 'dists'}[mode]
        self.setIconSize(QtCore.QSize(32, 32))
        item.setIcon(gui_common.load_icon(iconame))

    def ListWidgetEditEnd(self, editor, hint):
        ''' Slot for when item is done being edited '''
        newvalue = editor.text()
        index = self.currentRow()
        self.itemRenamed.emit(index, newvalue)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            menu = QtWidgets.QMenu(self)
            actRename = QtWidgets.QAction('Rename', self)
            menu.addAction(actRename)
            actRename.triggered.connect(lambda event, x=item: self.editItem(x))
            menu.popup(QtGui.QCursor.pos())


class ProjectDockWidget(QtWidgets.QWidget):
    ''' Project Dock '''
    addcomponent = QtCore.pyqtSignal()
    remcomponent = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.projectlist = CalculationsListWidget()
        self.btnadd = QtWidgets.QToolButton()
        self.btnrem = QtWidgets.QToolButton()
        self.btnadd.setText('+')
        self.btnrem.setText('–')  # endash
        self.btnadd.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.btnrem.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addWidget(self.btnadd)
        hlayout.addWidget(self.btnrem)
        hlayout.addStretch()
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hlayout)
        layout.addWidget(self.projectlist)
        self.setLayout(layout)

        self.btnadd.clicked.connect(self.addcomponent)
        self.btnrem.clicked.connect(self.remove)

    def remove(self):
        ''' Remove an item from the project dock '''
        idx = self.projectlist.currentRow()
        if idx >= 0:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Suncal')
            msgbox.setText(f'Remove {self.projectlist.currentItem().text()} from project?')
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if msgbox.exec_() == QtWidgets.QMessageBox.Yes:
                self.projectlist.takeItem(idx)
                self.remcomponent.emit(idx)


class InsertCalcWidget(QtWidgets.QWidget):
    ''' Window for selecting and inserting a new calculation component '''
    newcomp = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.btnUnc = ToolButton('Uncertainty\nPropagation', gui_common.load_icon('target'))
        self.btnCurve = ToolButton('Curve Fit', gui_common.load_icon('curvefit'))
        self.btnRisk = ToolButton('Risk\nAnalysis', gui_common.load_icon('risk'))
        self.btnSweep = ToolButton('Uncertainty\nSweep', gui_common.load_icon('targetlist'))
        self.btnReverse = ToolButton('Reverse\nPropagation', gui_common.load_icon('calipers'))
        self.btnReverseSweep = ToolButton('Reverse\nSweep', gui_common.load_icon('rulersweep'))
        self.btnDataset = ToolButton('Data Sets &&\nANOVA', gui_common.load_icon('boxplot'))
        self.btnInterval = ToolButton('Calibration\nIntervals', gui_common.load_icon('interval'))
        self.btnDist = ToolButton('Distribution\nExplorer', gui_common.load_icon('dists'))

        self.btnWizard = QtWidgets.QPushButton('Uncertainty Wizard')
        self.btnWizard.setIconSize(QtCore.QSize(32, 32))
        self.btnWizard.setIcon(gui_common.load_icon('wizard'))
        self.btnWizard.setFixedSize(84*3+10, int(84/1.5))

        self.btnUnc.clicked.connect(lambda x: self.newcomp.emit('uncertainty'))
        self.btnCurve.clicked.connect(lambda x: self.newcomp.emit('curvefit'))
        self.btnRisk.clicked.connect(lambda x: self.newcomp.emit('risk'))
        self.btnSweep.clicked.connect(lambda x: self.newcomp.emit('sweep'))
        self.btnReverse.clicked.connect(lambda x: self.newcomp.emit('reverse'))
        self.btnReverseSweep.clicked.connect(lambda x: self.newcomp.emit('reversesweep'))
        self.btnDataset.clicked.connect(lambda x: self.newcomp.emit('data'))
        self.btnDist.clicked.connect(lambda x: self.newcomp.emit('distributions'))
        self.btnInterval.clicked.connect(lambda x: self.newcomp.emit('interval'))
        self.btnWizard.clicked.connect(lambda x: self.newcomp.emit('wizard'))

        glayout = QtWidgets.QGridLayout()
        glayout.addWidget(self.btnUnc, 0, 0)
        glayout.addWidget(self.btnReverse, 0, 1)
        glayout.addWidget(self.btnDataset, 0, 2)
        glayout.addWidget(self.btnSweep, 1, 0)
        glayout.addWidget(self.btnReverseSweep, 1, 1)
        glayout.addWidget(self.btnCurve, 1, 2)
        glayout.addWidget(self.btnRisk, 2, 0)
        glayout.addWidget(self.btnInterval, 2, 1)
        glayout.addWidget(self.btnDist, 2, 2)

        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignHCenter)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel('Select Calculation Type'))
        layout.addLayout(glayout)
        layout.addSpacing(15)
        layout.addWidget(self.btnWizard)
        layout.addStretch()
        self.setLayout(layout)

    def help_report(self):
        ''' Get main help text '''
        return MainHelp.project_types()


class HelpWindow(QtWidgets.QDockWidget):
    ''' Dock widget for showing help information '''
    def __init__(self):
        super().__init__('Help')
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable |
                         QtWidgets.QDockWidget.DockWidgetMovable |
                         QtWidgets.QDockWidget.DockWidgetFloatable)
        self.helppane = gui_widgets.MarkdownTextEdit()
        self.setWidget(self.helppane)

    def setHelp(self, rpt):
        ''' Set the report to display '''
        self.helppane.setReport(rpt)


class MainGUI(QtWidgets.QMainWindow):
    ''' Main GUI holds the project, stack of project component widgets, insert component widget, and menus '''
    openconfigfolder = QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.HomeLocation)[0]

    PG_TOP_INSERT = 0   # topstack index for insert and project page
    PG_TOP_PROJECT = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Suncal - v' + version.__version__)
        gui_widgets.centerWindow(self, 1200, 900)
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

        self.project = Project()  # New empty project

        # project dock
        self.projdock = QtWidgets.QDockWidget('Project Components', self)
        self.projdock.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable |
                                  QtWidgets.QDockWidget.DockWidgetMovable |
                                  QtWidgets.QDockWidget.DockWidgetFloatable)
        self.dockwidget = ProjectDockWidget()
        self.dockwidget.projectlist.currentRowChanged.connect(self.changepage)
        self.projdock.setWidget(self.dockwidget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.projdock)
        self.projdock.setVisible(False)
        self.helpdock = HelpWindow()
        self.helpdock.setVisible(False)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.helpdock)

        self.pginsert = InsertCalcWidget()
        self.projstack = QtWidgets.QStackedWidget()   # Stack for all project components
        self.topstack = QtWidgets.QStackedWidget()    # Stack for Insert page and Project
        self.topstack.addWidget(self.pginsert)
        self.topstack.addWidget(self.projstack)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.topstack)
        self.setCentralWidget(self.topstack)

        self.pginsert.newcomp.connect(self.add_component)
        self.dockwidget.addcomponent.connect(self.insert_clicked)
        self.dockwidget.remcomponent.connect(self.remove_component)
        self.dockwidget.projectlist.itemRenamed.connect(self.rename)

        # Menu
        self.menubar = QtWidgets.QMenuBar()
        actPrefs = QtWidgets.QAction('&Preferences...', self)
        actPrefs.triggered.connect(self.edit_prefs)
        actNew = QtWidgets.QAction('&New project', self)
        actNew.triggered.connect(self.newproject)
        actOpen = QtWidgets.QAction('&Load project...', self)
        actOpen.triggered.connect(self.load_project)
        actSave = QtWidgets.QAction('&Save project...', self)
        actSave.triggered.connect(self.save_project)
        actQuit = QtWidgets.QAction('E&xit', self)
        actQuit.triggered.connect(self.close)
        actAbout = QtWidgets.QAction('&About', self)
        actAbout.triggered.connect(page_about.show)
        actManual = QtWidgets.QAction('&User Manual', self)
        actManual.triggered.connect(self.showmanual)
        actHelp = QtWidgets.QAction('&Help', self)
        actHelp.triggered.connect(self.open_page_help)

        # Project Menu
        self.actInsertCalc = QtWidgets.QAction('Add Calculation...', self)
        self.actInsertCalc.triggered.connect(self.insert_clicked)
        self.actCalcAll = QtWidgets.QAction('Calculate All', self)
        self.actCalcAll.triggered.connect(self.calculate_all)
        self.actSaveReport = QtWidgets.QAction('Save Project Report...', self)
        self.actSaveReport.triggered.connect(self.save_report)

        self.menuProj = QtWidgets.QMenu('&Project')
        self.menuProj.addAction(actNew)
        self.menuProj.addAction(actOpen)
        self.menuProj.addAction(actSave)
        self.menuProj.addSeparator()
        self.menuProj.addAction(self.actInsertCalc)
        self.menuProj.addAction(self.actCalcAll)
        self.menuProj.addAction(self.actSaveReport)
        self.menuProj.addSeparator()
        self.menuProj.addAction(actPrefs)
        self.menuProj.addAction(actQuit)
        self.menubar.addMenu(self.menuProj)

        # COMPONENT-SPECIFIC menus go HERE

        # Window Menu
        self.actUnits = QtWidgets.QAction('Units Converter', self)
        self.actUnits.triggered.connect(self.showunits)
        self.actTtable = QtWidgets.QAction('t-Table', self)
        self.actTtable.triggered.connect(self.showttable)
        self.actViewProj = self.projdock.toggleViewAction()
        self.actViewProj.setText('Show project tree')
        self.menuWind = QtWidgets.QMenu('&Window')
        self.menuWind.addAction(self.actUnits)
        self.menuWind.addAction(self.actTtable)
        self.menuWind.addAction(self.actViewProj)
        self.menubar.addMenu(self.menuWind)

        # Help Menu
        self.menuHelp = QtWidgets.QMenu('&Help')
        self.menuHelp.addAction(actHelp)
        self.menuHelp.addAction(actManual)
        self.menuHelp.addAction(actAbout)
        self.menubar.addMenu(self.menuHelp)
        self.setMenuBar(self.menubar)

        self.menucomponentbefore = self.menuWind.menuAction()
        gui_common.set_plot_style()
        gui_common.settings.registerUnits()

    def insert_clicked(self):
        ''' Insert a new calculation '''
        self.projdock.setVisible(True)
        self.topstack.setCurrentIndex(self.PG_TOP_INSERT)

    def add_component(self, typename='uncertainty'):
        ''' Insert a new project component

            Parameters
            ----------
            typename: str
                Type of calculation to add.
        '''
        if typename == 'uncertainty':
            item = ProjectUncert()
            item.seed = gui_common.settings.getRandomSeed()
            item.nsamples = gui_common.settings.getRandomSeed()
            self.project.add_item(item)
            widget = page_uncert.UncertPropWidget(item)
            widget.newtype.connect(self.change_component)
        elif typename == 'wizard':
            item = ProjectUncertWizard()
            self.project.add_item(item)
            widget = page_wizard.UncertWizard(item)
        elif typename == 'curvefit':
            item = ProjectCurveFit()
            item.seed = gui_common.settings.getRandomSeed()
            self.project.add_item(item)
            widget = page_curvefit.CurveFitWidget(item)
        elif typename == 'risk':
            item = ProjectRisk()
            self.project.add_item(item)
            widget = page_risk.RiskWidget(item)
        elif typename == 'sweep':
            item = ProjectSweep()
            item.seed = gui_common.settings.getRandomSeed()
            item.nsamples = gui_common.settings.getRandomSeed()
            self.project.add_item(item)
            widget = page_sweep.UncertSweepWidget(item)
            widget.newtype.connect(self.change_component)
        elif typename == 'reverse':
            item = ProjectReverse()
            item.seed = gui_common.settings.getRandomSeed()
            item.nsamples = gui_common.settings.getRandomSeed()
            self.project.add_item(item)
            widget = page_reverse.UncertReverseWidget(item)
            widget.newtype.connect(self.change_component)
        elif typename == 'reversesweep':
            item = ProjectReverseSweep()
            item.seed = gui_common.settings.getRandomSeed()
            item.nsamples = gui_common.settings.getRandomSeed()
            self.project.add_item(item)
            widget = page_sweep.UncertReverseSweepWidget(item)
            widget.newtype.connect(self.change_component)
        elif typename == 'data':
            item = ProjectDataSet()
            self.project.add_item(item)
            widget = page_dataset.DataSetWidget(item)
        elif typename == 'distributions':
            item = ProjectDistExplore()
            self.project.add_item(item)
            widget = page_distribution.DistWidget(item)
        elif typename == 'interval':
            item = page_interval.getNewIntervalCalc()
            self.project.add_item(item)
            widget = page_interval.IntervalWidget(item)
        else:
            raise NotImplementedError

        self.dockwidget.projectlist.addItem(typename, item.name)
        self.projdock.setVisible(self.project.count() > 1)
        self.menubar.insertMenu(self.menucomponentbefore, widget.get_menu())
        self.projstack.addWidget(widget)
        self.topstack.setCurrentIndex(self.PG_TOP_PROJECT)
        self.dockwidget.projectlist.blockSignals(True)
        self.dockwidget.projectlist.setCurrentRow(self.dockwidget.projectlist.count()-1)
        self.dockwidget.projectlist.blockSignals(False)
        self.changepage(self.projstack.count()-1)
        with suppress(AttributeError):
            widget.change_help.connect(self.set_page_help)
            widget.open_help.connect(self.open_page_help)
        self.set_page_help()

    def change_component(self, config, newtype):
        ''' Convert item into new type (e.g. uncertprop into reverse) '''
        if newtype == 'reverse':
            item = ProjectReverse.from_config(config)
            self.project.add_item(item)
            widget = page_reverse.UncertReverseWidget(item)
            widget.newtype.connect(self.change_component)
        elif newtype == 'sweep':
            item = ProjectSweep.from_config(config)
            self.project.add_item(item)
            widget = page_sweep.UncertSweepWidget(item)
            widget.newtype.connect(self.change_component)
        elif newtype == 'uncertainty':
            item = ProjectUncert.from_config(config)
            self.project.add_item(item)
            widget = page_uncert.UncertPropWidget(item)
            widget.newtype.connect(self.change_component)
        elif newtype == 'reversesweep':
            item = ProjectReverseSweep.from_config(config)
            self.project.add_item(item)
            widget = page_sweep.UncertReverseSweepWidget(item)
            widget.newtype.connect(self.change_component)
        else:
            raise ValueError(f'Unknown calculation type {newtype}')

        item.name = newtype
        self.dockwidget.projectlist.addItem(newtype, item.name)
        self.projdock.setVisible(self.project.count() > 1)
        self.menubar.insertMenu(self.menucomponentbefore, widget.get_menu())
        self.projstack.addWidget(widget)
        self.topstack.setCurrentIndex(self.PG_TOP_PROJECT)
        self.dockwidget.projectlist.blockSignals(True)
        self.dockwidget.projectlist.setCurrentRow(self.dockwidget.projectlist.count()-1)
        self.dockwidget.projectlist.blockSignals(False)
        self.changepage(self.projstack.count()-1)

    def remove_component(self, index):
        ''' Remove component at index. Show insert page if no calcs left. '''
        self.project.rem_item(index)
        widget = self.projstack.widget(index)
        self.menubar.removeAction(widget.get_menu().menuAction())
        self.projstack.removeWidget(widget)
        if self.project.count() == 0:
            self.topstack.setCurrentIndex(self.PG_TOP_INSERT)
        self.set_page_help()

    def changepage(self, index):
        ''' Change the current component page '''
        if index > -1:
            with suppress(AttributeError):
                self.projstack.currentWidget().get_menu().menuAction().setVisible(False)

            self.projstack.setCurrentIndex(index)
            self.topstack.setCurrentIndex(self.PG_TOP_PROJECT)
            self.projstack.currentWidget().get_menu().menuAction().setVisible(True)
            with suppress(AttributeError):
                self.set_page_help()

    def showmanual(self):
        ''' Show the user manual '''
        filename = gui_common.resource_path('SUNCALmanual.pdf')
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(r'file:/' + filename))

    def open_page_help(self):
        ''' Make the help dock visible '''
        self.helpdock.setVisible(True)
        self.set_page_help()

    def set_page_help(self):
        ''' Change the help report to display, get it from the active widget '''
        if self.topstack.currentIndex() == self.PG_TOP_INSERT:
            rpt = self.topstack.currentWidget().help_report()
        else:
            try:
                rpt = self.projstack.currentWidget().help_report()
            except AttributeError:
                rpt = report.Report()
                rpt.add('No help available')
        self.helpdock.setHelp(rpt)

    def edit_prefs(self):
        ''' Show preferences dialog '''
        dlg = configmgr.PgSettingsDlg()
        dlg.exec_()
        gui_common.set_plot_style()

    def save_project(self):
        ''' Save project to file. '''
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption='Select file to save', filter='Suncal YAML (*.yaml);;All files (*.*)')
        if fname:
            for i in range(self.projstack.count()):
                # Update each project component with values from page
                widget = self.projstack.widget(i)
                widget.update_proj_config()
            self.project.save_config(fname)

    def build_config(self):
        ''' Refresh configuration dictionary defining the project '''
        config = []
        for item in self.project.items:
            config.append(item.get_config())

    def load_project(self):
        ''' Load a project from file, prompting user for filename '''
        fname, self.openconfigfolder = QtWidgets.QFileDialog.getOpenFileName(
            caption='Select file to open', directory=self.openconfigfolder,
            filter='Suncal YAML (*.yaml);;All files (*.*)')
        if fname:
            self.newproject()
            oldproject = self.project  # just in case things go wrong...
            self.project = Project.from_configfile(fname)
            if self.project is not None:
                for i in range(self.project.count()):
                    mode = self.project.get_mode(i)
                    if mode == 'uncertainty':
                        widget = page_uncert.UncertPropWidget(self.project.items[i])
                        widget.newtype.connect(self.change_component)
                    elif mode == 'wizard':
                        widget = page_wizard.UncertWizard(self.project.items[i])
                    elif mode == 'sweep':
                        widget = page_sweep.UncertSweepWidget(self.project.items[i])
                        widget.newtype.connect(self.change_component)
                    elif mode == 'reverse':
                        widget = page_reverse.UncertReverseWidget(self.project.items[i])
                        widget.newtype.connect(self.change_component)
                    elif mode == 'reversesweep':
                        widget = page_sweep.UncertReverseSweepWidget(self.project.items[i])
                        widget.newtype.connect(self.change_component)
                    elif mode == 'risk':
                        widget = page_risk.RiskWidget(self.project.items[i])
                    elif mode == 'curvefit':
                        widget = page_curvefit.CurveFitWidget(self.project.items[i])
                    elif mode == 'data':
                        widget = page_dataset.DataSetWidget(self.project.items[i])
                    elif mode == 'distributions':
                        widget = page_distribution.DistWidget(self.project.items[i])
                    elif mode.startswith('interval'):
                        widget = page_interval.IntervalWidget(self.project.items[i])
                    else:
                        raise NotImplementedError
                    self.dockwidget.projectlist.addItem(mode, self.project.items[i].name)
                    self.menubar.insertMenu(self.menucomponentbefore, widget.get_menu())
                    widget.get_menu().menuAction().setVisible(False)
                    self.projstack.addWidget(widget)
                self.dockwidget.projectlist.setCurrentRow(0)
                self.projdock.setVisible(True)
                self.topstack.setCurrentIndex(self.PG_TOP_PROJECT)
            else:
                QtWidgets.QMessageBox.warning(self, 'Suncal', 'Error loading file!')
                self.project = oldproject

    def newproject(self):
        ''' Clear/new project '''
        ok = True
        if self.project is not None and self.project.count() > 0:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Suncal')
            msgbox.setText('Existing project components will be removed. Are you sure?')
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            ok = msgbox.exec_() == QtWidgets.QMessageBox.Yes
        if ok:
            self.projstack.blockSignals(True)
            self.project = Project()
            while self.projstack.count() > 0:  # No clear() method available
                widget = self.projstack.widget(0)
                self.menubar.removeAction(widget.get_menu().menuAction())
                self.projstack.removeWidget(widget)
            self.projstack.blockSignals(False)
            self.topstack.setCurrentIndex(self.PG_TOP_INSERT)
            self.dockwidget.projectlist.clear()

    def rename(self, index, name):
        ''' Rename an item in the project '''
        self.project.rename_item(index, name)

    def showttable(self):
        ''' Show a window with t/k confidence calculator '''
        dlg = page_ttable.TTableDialog(parent=self)
        dlg.show()

    def showunits(self):
        ''' Show a window with units converter '''
        dlg = page_units.UnitsConverter(parent=self)
        dlg.show()

    def calculate_all(self):
        ''' Run calculate() on all project components '''
        for i in range(self.projstack.count()):
            widget = self.projstack.widget(i)
            widget.calculate()

    def save_report(self):
        ''' Save report of all items in project '''
        r = report.Report()
        for i in range(self.project.count()):
            r.hdr(self.project.items[i].name, level=1)
            widget = self.projstack.widget(i)
            try:
                wreport = widget.get_report()
            except AttributeError:
                wreport = None
            if wreport is None:
                r.txt('Calculation not run\n\n')
            else:
                r.append(wreport)
                r.div()
        gui_widgets.savereport(r)

    def closeEvent(self, event):
        ''' Window is being closed. Verify. '''
        if self.project.count() > 0:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Suncal')
            msgbox.setText('Are you sure you want to close?')
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if msgbox.exec_() == QtWidgets.QMessageBox.No:
                event.ignore()
            else:
                event.accept()
        else:
            event.accept()


def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    app = QtWidgets.QApplication(sys.argv)

    maingui = MainGUI()
    icon = gui_common.get_logo()
    maingui.setWindowIcon(icon)
    maingui.show()
    app.exec_()


if __name__ == '__main__':
    main()
