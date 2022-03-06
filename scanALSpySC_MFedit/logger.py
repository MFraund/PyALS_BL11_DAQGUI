import logging
import sys

from PyQt5.QtCore import QObject,\
                         pyqtSignal

from PyQt5.QtWidgets import QDialog, \
                        QVBoxLayout, \
                        QPushButton, \
                        QTextBrowser,\
                        QApplication

logger = logging.getLogger(__name__)

class XStream(QObject):
    _stdout = None
    _stderr = None

    messageWritten = pyqtSignal(str)

    def flush( self ):
        pass

    def fileno( self ):
        return -1

    def write( self, msg ):
        if ( not self.signalsBlocked() ):
            self.messageWritten.emit(msg)

    @staticmethod
    def stdout():
        if ( not XStream._stdout ):
            XStream._stdout = XStream()
            sys.stdout = XStream._stdout
        return XStream._stdout

    @staticmethod
    def stderr():
        if ( not XStream._stderr ):
            XStream._stderr = XStream()
            sys.stderr = XStream._stderr
        return XStream._stderr

class MyDialog(QDialog):
    def __init__( self, parent = None ):
        super(MyDialog, self).__init__(parent)

        # setup the ui
        self._console = QTextBrowser(self)
        self._button  = QPushButton(self)
        self._button.setText('Test Me')

        # create the layout
        layout = QVBoxLayout()
        layout.addWidget(self._console)
        layout.addWidget(self._button)
        self.setLayout(layout)

        # create connections
        XStream.stdout().messageWritten.connect( self._console.insertPlainText )
        XStream.stderr().messageWritten.connect( self._console.insertPlainText )

        self._button.clicked.connect(self.test)

    def test( self ):
        # print some stuff
        print('testing'  )
        print('testing2' )

        # log some stuff
        logger.debug('Testing debug')
        logger.info('Testing info')
        logger.warning('Testing warning')
        logger.error('Testing error')

        # error out something

if ( __name__ == '__main__' ):
    logging.basicConfig()

    app = None
    if ( not QApplication.instance() ):
        app = QApplication([])

    dlg = MyDialog()
    dlg.show()

    if ( app ):
        app.exec_()
