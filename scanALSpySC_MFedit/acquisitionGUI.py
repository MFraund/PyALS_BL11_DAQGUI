import os

import time
import pandas as pd
import numpy as np

from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, QSettings
from acquisitionWindow import  Ui_MainWindow

from logger import XStream
import json

from ntplib import NTPClient
from epics import PV

import struct
from bitstring import BitArray

#try:
#    from readTDC import TDC
#except:
#    class TDC():
#        def init(self): pass
#        def deinit(self): pass
#        def open_callback_pipe(self): pass
        
import scTDC

from prodigy_remote import ProdigyRemote
from write_ports import PhaseShifter

#%% TDC user callbacks
class callback(scTDC.usercallbacks_pipe):
    def __init__(self, lib, dev_desc):
        super().__init__(lib, dev_desc) # <-- mandatory
        self.reset_counters()
    
    def on_millisecond(self):
        self.msecs += 1
        
        if self.msecs and (not (self.msecs % 1000)):
            print("Count rate: %7i per sec" % ((self.counts - self.co) / (self.msecs- self.mo) *1000 ), 
                  " after %5i secs." %(self.msecs/1000)
                  )
           
            self.mo  = self.msecs
            self.co = self.counts

    def on_start_of_meas(self):
        self.reset_counters()
       

    def on_end_of_meas(self):
        pass

    def on_tdc_event(self, tdc_events, nr_tdc_events):
        self.counts += nr_tdc_events


    def on_dld_event(self, dld_events, nr_dld_events):
        self.counts += nr_dld_events
    
    def reset_counters(self):
        self.counts = 0
        self.msecs = 0
        
        self.co = 0
        self.mo = 0
        

#%% Main Window
class AcquisitionUI(QtWidgets.QMainWindow, Ui_MainWindow):
    
    def __init__(self, debug=True):
        super(AcquisitionUI, self).__init__()

        self.setupUi(self)
        self.settings = QSettings('AqcuisitionUI','GUI_Settings')
        self.DEBUG = debug

        ### Logging
        if not self.DEBUG:
            XStream.stdout().messageWritten.connect( self.logBrowser.insertPlainText )
            XStream.stderr().messageWritten.connect( self.logBrowser.insertPlainText )

        ### Meta Params
        self.freq = PV('MOCounter:FREQUENCY')
        self.ntp = NTPClient()

        ### Timer
        self.cps_timer = QTimer()
        # self.cps_timer.timeout.connect(self.update_counts)
        self.tStart = time.time()
        self.msecs_cur = 0
        self.msecs_old = 0
        self.dldev_cur = 0
        self.dldev_old = 0

        #%% Open and Save Files
        self.pushBrowseFolder.clicked.connect(self.selectDirectory)

        self.dataFolder = 'C:\\Data\\2021\\November\\Gessner\\Data'
        self.dataFolderLineEdit.setText(self.dataFolder)

        dateTime = time.localtime()
        self.dataFileName = '%02i%02i%02i' % (dateTime.tm_year - 2000, dateTime.tm_mon, dateTime.tm_mday)
        self.fileNameLineEdit.setText(self.dataFileName)

        self.runningValue = 1
        self.runningNoSpinBox.setValue(self.runningValue)

        self.createFileName()
        self.checkExistingPath()



        #%% Devices
        self.ini_file = 'tdc_gpx3_from_surface_concept_with_ext_start.ini' ######Change to be same folder
        # self.ini_file = 'tdc_gpx3_from_surface_concept.ini' ######Change to be same folder
        
        self.tdc = scTDC.Device(inifilepath=self.ini_file,
                        autoinit=False) #TDC(debug=self.DEBUG)
                        

        self.ps = PhaseShifter()
        self.remote = ProdigyRemote(debug=self.DEBUG)

        #%% TDC Section
        
        self.pushInitTDC.clicked.connect(  self.initTDC   )
        self.pushDeinitTDC.clicked.connect(self.deinitTDC ) 
        self.pushSelectIni.clicked.connect(self.selectIniFile ) 
        self.iniFileLineEdit.setText(os.path.basename(self.ini_file))

        #%% Prodigy Section
        self.pushConnectProdigy.clicked.connect(    self.connectProdigy    )
        self.pushDisconnectProdigy.clicked.connect( self.disconnectProdigy ) 
        self.pushApplyVoltages.clicked.connect(     self.applyVoltages     )
        self.pushSetSafeState.clicked.connect(      self.setSafeState      )

        #%% Phase Shifter Section
        self.pushInitPhaseShifter.clicked.connect( self.initPhaseShifter)
        self.pushSetPhaseShifter.clicked.connect( self.setPhaseShifter)

        ### Phase Shifter Scanning Section
        self.pushAddRow.clicked.connect( self.addScanRow)
        self.pushDeleteRow.clicked.connect( self.deleteScanRow)
        self.pushScanAcquire.clicked.connect( self.AcquirePhaseShifterScan)
        self.testPS.clicked.connect( self.stepthroughPhaseShifter)
        self.pushSaveScan.clicked.connect( self.savePSScans)
        self.pushLoadScan.clicked.connect( self.loadPSScans)
        
        #%% Manipulator Calibration Section
        self.calDict = self.settings.value('CalDict')
        # self.doubleSpinBox_CalAH.setValue(self.calDict['CalAH'])
        # self.doubleSpinBox_CalAV.setValue(self.calDict['CalAV'])
        # self.doubleSpinBox_CalBH.setValue(self.calDict['CalBH'])
        # self.doubleSpinBox_CalBV.setValue(self.calDict['CalBV'])
        
        self.doubleSpinBox_CalAH.editingFinished.connect(self.Manipulator2Picomotor)
        self.doubleSpinBox_CalAV.editingFinished.connect(self.Manipulator2Picomotor)
        self.doubleSpinBox_CalBH.editingFinished.connect(self.Manipulator2Picomotor)
        self.doubleSpinBox_CalBV.editingFinished.connect(self.Manipulator2Picomotor)
        self.spinBox_DevH.editingFinished.connect(self.Manipulator2Picomotor)
        self.spinBox_DevV.editingFinished.connect(self.Manipulator2Picomotor)
        
        #%% Voltages

        for item in ['"LargeArea"',
                     '"SmallArea"',
                    ]:
            self.lensModeComboBox.addItem(item)

        for item in ['"10V"', '"100V"', '"400V"', '"1.5kV"', '"3.5kV"',]:
            self.scanRangeComboBox.addItem(item)
        self.scanRangeComboBox.setCurrentIndex(4)
        

        self.voltKnobs ={
                        '"LensMode"'                : self.lensModeComboBox,
                        '"ScanRange"'               : self.scanRangeComboBox,
                        '"Kinetic Energy"'          : self.kineticEnergySpinBox,
                        '"Pass Energy"'             : self.passEnergySpinBox,
                        '"Detector Voltage"'        : self.detectorVoltageSpinBox,
                        '"DLD Voltage"'             : self.dLDVoltageSpinBox,
                        '"Bias Voltage Electrons"'  : self.biasElectronsSpinBox,
                        '"Coil Current"'            : self.coilCurrentSpinBox,
#                
                        '"Deflection X"'            : self.deflectionXDoubleSpinBox,
                        '"Deflection Y"'            : self.deflectionYDoubleSpinBox,
                        '"L1"'                      : self.l1DoubleSpinBox,
                        # '"L2"'                      : self.l2DoubleSpinBox,                       
                        '"Pre Defl X"'              : self.preDeflXDoubleSpinBox,
                        '"Pre Defl Y"'              : self.preDeflYDoubleSpinBox,
                        '"Focus Displacement 1"'    : self.focus1DoubleSpinBox,
                        '"Focus Displacement 2"'    : self.focus2DoubleSpinBox,
                        # '"Aux Voltage"'             : self.auxVoltageSpinBox,
                        }
        self.voltDict = {}
        
        self.pushSaveVoltages.clicked.connect( self.saveVoltages )
        self.pushLoadVoltages.clicked.connect( self.loadVoltages )


        ### Acquire Static Spectrum
        self.pushStaticAcquire.clicked.connect( self.acquireStatic ) 
        self.pushScanAbort.setEnabled( False )


        self.cps_timer.start(1000)

        

    #%% Handle Closing
    def closeEvent(self, event):
        
        self.settings.setValue('PicomotorCal', self.calDict)
        if self.remote.connected:
            self.remote.disconnect()

        self.deinitTDC()

#       if self.tdc.is_initialized:
#           self.tdc.deinit()


    #%% Files and Directory


    def createFileName(self):
        path = os.path.join(self.dataFolder, self.dataFileName)
        path += '-run%03i.h5' % (self.runningNoSpinBox.value() ) 
        self.path = path
        print(path)

    def checkExistingPath(self):
        print(self.path)
        file_exists = os.path.exists(self.path)
        # pathsplit = os.path.split(self.path)
        # print(pathsplit[0] + '\\PS_Scan_' + pathsplit[1][:-3])
        folder_exists = os.path.exists(self.dataFolder + '\\' + 'PS_Scan_' + self.dataFileName + '-run%03i' % (self.runningNoSpinBox.value()))
        print(self.dataFolder + '\\' + 'PS_Scan_' + self.dataFileName + '-run%03i' % (self.runningNoSpinBox.value()))
        while file_exists or folder_exists:
            self.runningValue += 1
            self.runningNoSpinBox.setValue(self.runningValue)
            self.createFileName()
            file_exists = os.path.exists(self.path)
            folder_exists = os.path.exists(self.dataFolder + '\\' + 'PS_Scan_' + self.dataFileName + '-run%03i' % (self.runningNoSpinBox.value()))

    def selectDirectory(self):
        self.dataFolder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Open File', 'C:\\Data\\',
                                                          )
        self.dataFolderLineEdit.setText(self.dataFolder)

    ### Count Timer

    def update_counts(self):
        if self.tdc.is_initialized():
            self.msecs_old = self.msecs_cur
            self.dldev_old = self.dldev_cur
            

#            self.msecs_cur, self.dldev_cur = self.tdc.get_time_and_counts()
            
            if (self.cb.msecs):
                self.cps = (self.cb.counts//self.cb.msecs * 1000)
            else:
                self.cps = 0
#            if self.DEBUG:
#                print("Count rate: ", self.cb.msecs, " Seconds elapsed: ", time.time() - self.tStart  )

            self.lcdCPS.display(self.cps)

#            if self.msecs_cur:
            self.progressScan.setValue( (time.time() - self.tStart) / (self.acquisitionTimeSecsSpinBox.value() ) * 100 )  ###an integer is required somewhere


    #%% TDC Methods

    def initTDC(self):
           
        retcode, errmsg = self.tdc.initialize()
        if retcode < 0:
            print("Error during initialization : ({}) {}".format(errmsg, retcode))
            return
        

        success, errmsg = self.tdc.hdf5_enable()
        if not success:
            print("Error while enabling HDF5 : " + errmsg)
            return
        else: 
            self.statusbar.showMessage("TDC Ready.")
            
        a = scTDC.HDF5DataSelection # short alias
        self.datasel = scTDC.HDF5DataSelection(a.X | a.TIME)
        
        self.cb = callback(self.tdc.lib, self.tdc.dev_desc)
        

    def deinitTDC(self):
        if self.tdc.is_initialized():
            self.tdc.hdf5_disable()
            self.tdc.deinitialize()
        


    def selectIniFile(self):
        self.ini_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', 'C:\\Data\\2021\\November\\Gessner',
                                                          )
        self.iniFileLineEdit.setText(self.ini_file)
        self.tdc.inifile = self.ini_file



    #%% Prodigy Remote Connection
    
    def connectProdigy(self):
        if not self.remote.connected:
            self.remote.connect()
            self.remote.allParams = self.remote.getParams()
            self.statusbar.showMessage("Prodigy connected.")

    def disconnectProdigy(self):
        if self.remote.connected:
            self.remote.disconnect()

    def applyVoltages(self):
        self.gatherVoltages()
        self.remote.analyzr_volts.update(self.voltDict)

        if self.remote.connected:
            self.statusbar.showMessage('Ramping Voltages...')
            self.remote.setVoltagesDirectly(self.voltDict['"Kinetic Energy"'],
                                            self.voltDict['"Pass Energy"']   )    
            self.statusbar.showMessage('Alrighty.')

    def setSafeState(self):
        if self.remote.connected:
            self.statusbar.showMessage('Deduuuuhhh...')
            self.remote.setSafeState()
            self.statusbar.showMessage('All voltages down.')

    def gatherVoltages(self):
        self.voltDict = {k: self.voltKnobs[k].value() if hasattr(self.voltKnobs[k], 'value') 
                                                      else self.voltKnobs[k].currentText()
                            for k in self.voltKnobs }
    def updateVoltages(self):
        for k in self.voltDict:
            v = self.voltDict[k]
            if hasattr(self.voltKnobs[k], 'setValue'):
                self.voltKnobs[k].setValue(v)
            else:
                self.voltKnobs[k].setCurrentText(v)


    def saveVoltages(self):
        self.gatherVoltages()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', 'C:\\Data\\',
                                                          )
        if os.path.exists(fname): os.remove(fname)
        with open(fname, mode='x') as f:
            f.write( json.dumps(self.voltDict) ) 

    def loadVoltages(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', 'C:\\Data\\2021\\November\\Gessner\\Scripts',
                                                          )
        with open(fname, mode='r') as f:
            self.voltDict = json.loads( ''.join( f.readlines() ) ) 
        
        self.lineVoltages.setText(fname)
        self.updateVoltages()


    #%% TDC Methods

    def acquireStatic(self):
        if self.tdc.is_initialized:
            self.statusbar.showMessage('Starting a Measurement')
            self.checkExistingPath()
            acquTime = self.acquisitionTimeSecsSpinBox.value()


            self.progressScan.setValue(0)
            self.progressScan.setMaximum(100)
            self.progressScan.reset()
            self.tStart = time.time()

            self.msecs_cur, self.dldev_cur = 0, 0
            self.msecs_old, self.dldev_old = 0, 0

        success, errmsg = self.tdc.hdf5_open(
            self.path, "output of example_hdf5.py", self.datasel)
        if not success:
            print("Error while opening HDF5 file : " + errmsg)
            return
        
        print("Starting a measurement")
        retcode, errmsg = self.tdc.do_measurement(time_ms=acquTime * 1000, synchronous = True)
        # self.cb.do_measurement(time_ms=acquTime * 1000, )
        
        if retcode < 0:
            print("Error while starting measurement : ({}) {}".format(
                errmsg, retcode))
        # print("Finished measurements")
        
        print("Closing the HDF5 file") # this is very important: the HDF5 will be
        # incomplete and most likely not even readable at all if it is not closed
        success, errmsg = self.tdc.hdf5_close()
        if not success:
            print("Error while closing the HDF5 file")

#            self.tdc.measure( acquTime * 1000 )
        else:
            print(" ---------- Measurement finished ----------" + self.dataFileName + '-run%03i.h5' % (self.runningNoSpinBox.value()))
        self.statusbar.showMessage(' ---------- Measurement finished ----------' + self.dataFileName + '-run%03i.h5' % (self.runningNoSpinBox.value()))

    def abortStatic(self):
        pass

    def scanKinEng(self):
        pass


    #%% Phase Shifter Methods
    def initPhaseShifter(self):
        self.ps = PhaseShifter(0)
        ### Would be good to test if connected before attempting connection
        #sometimes a second connect command is enough, this is a hack but idk
        #why it doesn't play nice sometimes
        try:
            self.ps.connect()
        except:
            self.ps.connect()
        
        
        self.ps.read()
        
        currdelay = self.ps.state.int
        
        self.lcdDelay.display(currdelay)
        self.delayPsecSpinBox.setValue(currdelay)
        self.statusbar.showMessage('Phase Shifter Connected...')
        # self.setPhaseShifter()
    
    def setPhaseShifter(self):
        # delay_val can be anything from 0 to 5000 ps but needs to
        # be converted before writing to the MCC DAQ board
        delay_val = self.delayPsecSpinBox.value()
        
        
        if delay_val < 0:
            print('no negative delays, setting to 0')
            delay_val = 0
        elif delay_val > 5000:
            print('delay out of range, setting to max')
            delay_val = 5000
        
        delaytowrite = delay_val // 5
        self.ps.set_delay(delaytowrite)
        
        self.lcdDelay.display(delay_val)
        
    def addScanRow(self):
        totrows = self.tableOfDelayRanges.rowCount()
        self.tableOfDelayRanges.insertRow(totrows)
        
    def deleteScanRow(self):
        totrows = self.tableOfDelayRanges.rowCount()
        print(totrows)
        if totrows == 0:
            pass
        else:
            self.tableOfDelayRanges.removeRow(totrows-1)
    
    def stepthroughPhaseShifter(self):
        nrows = self.tableOfDelayRanges.rowCount()
        daqtime = self.acquisitionTimePerStepSecsSpinBox.value()
    
        for row in range(nrows):
            startps = int(self.tableOfDelayRanges.item(row,0).text())
            endps = int(self.tableOfDelayRanges.item(row,1).text())
            stepsize = int(self.tableOfDelayRanges.item(row,2).text())
        
            nsteps = (endps - startps)//stepsize
        
            if row == nrows-1:
                nsteps = nsteps + 1
        
            for step in range(nsteps):
                self.delayPsecSpinBox.setValue(startps + stepsize*step)
                self.setPhaseShifter()
                
                time.sleep(daqtime)
        
    def AcquirePhaseShifterScan(self):
        
        if self.tdc.is_initialized:
            self.statusbar.showMessage('Starting a Measurement')
            self.checkExistingPath()
            self.tStart = time.time()
            self.msecs_cur, self.dldev_cur = 0, 0
            self.msecs_old, self.dldev_old = 0, 0
            
            subfolderpath = self.dataFolder + '\\' + 'PS_Scan_' + self.dataFileName + '-run%03i' % (self.runningNoSpinBox.value())
            os.mkdir(subfolderpath)
            
            
            nrows = self.tableOfDelayRanges.rowCount()
            daqtime = self.acquisitionTimePerStepSecsSpinBox.value()
        
            for row in range(nrows):
                startps = int(self.tableOfDelayRanges.item(row,0).text())
                endps = int(self.tableOfDelayRanges.item(row,1).text())
                stepsize = int(self.tableOfDelayRanges.item(row,2).text())
            
                nsteps = (endps - startps)//stepsize
            
                if row == nrows-1:
                    nsteps = nsteps + 1
            
                for step in range(nsteps):
                    self.delayPsecSpinBox.setValue(startps + stepsize*step)
                    self.setPhaseShifter()
                    
                    
                    ps_filename = self.dataFileName + '-run%03i' % (self.runningNoSpinBox.value()) + '_ps%03i.h5' % (self.delayPsecSpinBox.value())
                    print(self.dataFolder)
                    print(subfolderpath)
                    print(ps_filename)
                    ps_newpath = os.path.join(self.dataFolder, subfolderpath, ps_filename)
                    
                    self.statusbar.showMessage('Setting Phaseshifter to ' + str(startps + stepsize*step))
                    
                    success, errmsg = self.tdc.hdf5_open(
                        ps_newpath, "output of example_hdf5.py", self.datasel)
                    if not success:
                        print("Error while opening HDF5 file : " + errmsg)
                        return
                    
                    print('Starting a Measurement')
                    # retcode, errmsg = self.tdc.do_measurement(time_ms=acquTime * 1000, synchronous = True)
                    self.cb.do_measurement(time_ms=daqtime * 1000, )
                    print('Finished Measurement')
                    
                    print('closing the HDF5 file')
                    success, errmsg = self.tdc.hdf5_close()
                    if not success:
                        print("Error while closing the HDF5 file")

                    else:
                        print(" ---------- Measurement finished ----------" + self.dataFileName + '-run%03i.h5' % (self.runningNoSpinBox.value()))
                    
                    time.sleep(1)
                    # self.progressScan.setBar((startps+stepsize*step)/5000)
            
            self.statusbar.showMessage('---------- Measurement finished ----------' + self.dataFileName + '-run%03i.h5' % (self.runningNoSpinBox.value()))
            
    def savePSScans(self):
        nrows = self.tableOfDelayRanges.rowCount()
        totcells = nrows * 3
        self.PSDict = {k: self.tableOfDelayRanges.item(k//3,k%3).text() for k in range(totcells)}       
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', 'C:\\Data\\2021\\November\\Gessner',
                                                             )
        
        if os.path.exists(fname): os.remove(fname)
        with open(fname, mode='x') as f:
            f.write( json.dumps(self.PSDict) ) 
    
    def loadPSScans(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', 'C:\\Data\\2021\\November\\Gessner',
                                                             )
        
        with open(fname, mode='r') as f:
            self.PSDict = json.loads( ''.join( f.readlines() ) ) 
        
        self.linePSScans.setText(fname)
        self.updatePSTable()
        
    def updatePSTable(self):
        totrows = self.tableOfDelayRanges.rowCount()
        for row in range(totrows):
            self.deleteScanRow()
            
        for k in self.PSDict:
            item = QTableWidgetItem(self.PSDict[k])
            if int(k)//3 == 0:
                self.addScanRow()
            # self.tableOfDelayRanges.item(int(k)//3, int(k)%3).setText(celltext)
            print(k)
            self.tableOfDelayRanges.setItem(int(k)//3, int(k)%3, item)
            # self.tableOfDelayRanges.setCurrentItem(item, command)
            
            
    def tableClick(self):
        nrows = self.tableofDelayRanges.rowCount()
        npts = 0
        for n in range(nrows):
            startpt = self.tableofDelayRanges.item(n,0)
            endpt = self.tableofDelayRanges.item(n,1)
            stepsize = self.tableofDelayRanges.item(n,2)
            currnpts = (endpt - startpt)//stepsize
            npts = npts + currnpts
            
        totaltime = npts * self.acquisitionTimePerStepSecsSpinBox.value()
        
        self.estTimeLine.setText(str(totaltime) + ' s')
            
            
    #%% Manip
    def Manipulator2Picomotor(self):
        #def some variables
        CalAH = self.doubleSpinBox_CalAH.value()
        CalAV = self.doubleSpinBox_CalAV.value()
        CalBH = self.doubleSpinBox_CalBH.value()
        CalBV = self.doubleSpinBox_CalBV.value()
        
        self.calDict = {'CalAH': CalAH, 'CalAV':CalAV, 'CalBH':CalBH, 'CalBV':CalBV}
        self.settings.setValue('PicomotorCal', self.calDict)
        
        Hdev = self.spinBox_DevH.value()
        Vdev = self.spinBox_DevV.value()
        
        calibration_matrix = [[CalAH, CalBH],
                          [CalAV, CalBV]]
        
        A = np.array(calibration_matrix)
        
        deviation_matrix = [Hdev, Vdev]
        
        B = np.array(deviation_matrix)
        
        X = (0, 0)
        try:
            X = np.linalg.inv(A).dot(B)
        except:
            self.statusbar.showMessage('Singular Matrix')
        
        #making sure they are rounded
        self.spinBox_StepA.setValue(int(X[0]))
        self.spinBox_StepB.setValue(int(X[1]))
    

#%% Run GUI Section
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
#   MainWindow = QtWidgets.QMainWindow()
    ui = AcquisitionUI()
    ui.show()
#   ui.setupUi(MainWindow)
#   MainWindow.show()
    sys.exit(app.exec_())
