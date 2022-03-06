import socket
from timeit import default_timer as timer



class ProdigyRemote(object):

    def __init__(self, debug=True):

        self.DEBUG = debug

        self.connected = False
        
        self.TCP_IP   = socket.gethostname()
        self.TCP_PORT = 7010

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.TCP_IP, self.TCP_PORT))
        self.sock.settimeout(30) # fifteen seconds timeout

        self.analyzr_volts = {'"LensMode"'                : '"LargeArea"',
                              '"ScanRange"'               : '"3.5kV"',
                              '"Polarity"'                : '"negative"',
                               '"Kinetic Energy"'          :   650,
                               '"Pass Energy"'             :   50,
                              '"Detector Voltage"'        :   1950,
                              '"DLD Voltage"'             :   0,
                              '"Bias Voltage Electrons"'  :   220,
#                             '"Bias Voltage Ions"'       :   2000,
                              '"Coil Current"'            :   0,
#
#                            }
#
#       self.prelens_volts = {
                              '"Deflection X"'    : -0.009,
                              '"Deflection Y"'    :  0.005,
                              '"L1"'              :  0.021,
                              '"Pre Defl X"'      :  0.013,
                              '"Pre Defl Y"'      : -0.054,
                              '"Stigmator"'       :  0
                             }

        self.analyzr_volts = {'"LensMode"'        : '"Accelerating"',
                              '"ScanRange"'       : '"1.5kV"',
                              '"Polarity"'        : '"negative"',
                               '"Kinetic Energy"'  :   200,
                               '"Pass Energy"'     :   50,
                              '"Detector Voltage"':   2150,
                              '"Bias Voltage Electrons"'     :   220,
                              '"Bias Voltage Ions"' :            2000,
# >>                            }
# >>
# >>        self.prelens_volts = {'"Suction Voltage"' : 0,
							  '"L_A2"'    :  0.1,
                              '"L_A4"'    : -0.08,
                              '"L_A6"'       :  -0.04,
                              '"L_B1"' :  -0.1,
                              '"L_B3"' : 0,
                              '"L_C1"' : 0.1,
							  '"L_C2"' : 0.1,
							  '"L_C3"' : 0,
							 }

### Added Dec 02, 2020 -- Variables for new prelens at the combined XPS/scattering setup
        self.analyzr_volts = {'"LensMode"'                  : '"SmallArea"',
                              '"ScanRange"'                 : '"1.5kV"',
                              '"Polarity"'                  : '"negative"',
                               '"Kinetic Energy"'            :   600,
                               '"Pass Energy"'               :   100,
                              '"Detector Voltage"'          :   2150,
                              '"DLD Voltage"'               :   0,
                              '"Bias Voltage Electrons"'    :   220,
                              '"Bias Voltage Ions"'         :  -500,
# >> Logical Variables
                              '"Focus Displacement 2"'  : 0.0,
                              '"Coil Current"'          : -15,
                              # '"Aux Voltage"'           : 0,
                              '"Deflection X"'          : -0.0126,
                              '"Deflection Y"'          :  0.03439,
                              '"Pre Defl X"'            :  0.0337,
                              '"Pre Defl Y"'            :  0.10225,
                              '"L1"'                    :  -0.271,
                              # '"L2"'                    :  0.0151,                              
                              '"Focus Displacement 1"'  : 0.0162 ,
							 }


#   def __new__(self):

# <><>        self.connect()
# <><>        self.allParams = self.getParams()


    def sendAndReceive(self, comd, tag=0x0100):
        cmdStr = b'?%04X '%tag + comd + b'\n'
#       cmdStr = cmdStr.encode('ascii')
        print(cmdStr)
        self.sock.sendall( cmdStr ) 
        resp = None
        beg = timer()
        while not resp:
            resp = self.sock.recv(2048)
        end = timer()
#       resp = resp.decode('ascii')

        if self.DEBUG:
            print('Response took %4.2f millisecs' % ((end-beg)*1e3) )

        if resp.find(b'OK') < 0:
#           return cmdStr
            raise RuntimeError( resp.decode('ascii') ) 

        return resp


    def connect(self, ):
        try:
            _ = self.sendAndReceive(b'Connect', tag=0x0100)
            self.connected = True
            print('Connected to Prodigy.')
        except:
            pass

    def disconnect(self, ):
        try:
            _ = self.sendAndReceive(b'Disconnect', tag=0xFFFF)
            print('Disconnected.')
            self.connected = False
        except: 
            pass

    def getParams(self, ):
        resp = self.sendAndReceive(b'GetAllAnalyzerParameterNames', tag=0x0110)
        allParams = resp.split(b'[')[-1][:-1].rstrip(b']').split(b',')
        return allParams
    
    def printAllParams(self):
        for parm in self.allParams:
            resp = self.sendAndReceive(b'GetAnalyzerParameterInfo ParameterName:' + parm)
            print(resp)

    def printAllParamValues(self):
        for parm in self.allParams:
            resp = self.sendAndReceive(b'GetAnalyzerParameterValue ParameterName:' + parm)
            print(resp)
        
    def setSafeState(self, ):
        _ = self.sendAndReceive(b'SetSafeState', tag=0x0FFF)

    def setVoltagesDirectly(self, 
                            kinEng=615, passEng=50,  ):
        self.analyzr_volts['"Kinetic Energy"'] = kinEng
        self.analyzr_volts['"Pass Energy"'] = passEng


        s  = [ ':'.join([ str(k), str(self.analyzr_volts[k]) ])
              for k in self.analyzr_volts]
#       s += [ ':'.join([ str(k), str(self.prelens_volts[k]) ])
#             for k in self.prelens_volts]
        s = ' '.join(s)
#       return ' '.join(s)
#       print(b'test' + bytes(s))
        pass
#       print(s)
        self.sendAndReceive(b'SetAnalyzerParameterValueDirectly ' + s.encode('ascii') , tag=0x010A)
        
    def startFEscan(self):
        self.sendAndReceive(b'DefineSpectrumFE')


if __name__ == '__main__':
    pr = ProdigyRemote()
    pr.printAllParams()
