# -*- coding: utf-8 -*-
"""
@copyright: (C) 2020 Surface Concept GmbH

Test HDF5 streaming.

"""

OUTPUTFILEPATH = "testA.h5" # warning! this file is overwritten if it exists 

def test_hdf5_streaming():
    """ Performs 1 measurement and streams DLD events to a HDF5 file. """
    import scTDC
    
    device = scTDC.Device(inifilepath="tdc_gpx3.ini",
                        autoinit=False)
    retcode, errmsg = device.initialize()
    if retcode < 0:
        print("Error during initialization : ({}) {}".format(errmsg, retcode))
        return
    

    success, errmsg = device.hdf5_enable()
    if not success:
        print("Error while enabling HDF5 : " + errmsg)
        return

    versionstr = device.hdf5_lib_version()
    print("Version of the libscTDC_hdf5 : " + versionstr)

    a = scTDC.HDF5DataSelection # short alias
    datasel = scTDC.HDF5DataSelection(a.X | a.TIME)

    print("Opening HDF5 file " + OUTPUTFILEPATH)    
    success, errmsg = device.hdf5_open(
        OUTPUTFILEPATH, "output of example_hdf5.py", datasel)
    if not success:
        print("Error while opening HDF5 file : " + errmsg)
        return
    
    print("Starting a measurement")
    retcode, errmsg = device.do_measurement(time_ms=15000, synchronous=True)
    if retcode < 0:
        print("Error while starting measurement : ({}) {}".format(
            errmsg, retcode))
    print("Finished measurements")
    
    print("Closing the HDF5 file") # this is very important: the HDF5 will be
    # incomplete and most likely not even readable at all if it is not closed
    success, errmsg = device.hdf5_close()
    if not success:
        print("Error while closing the HDF5 file")

    # (it is also possible to aggregate many measurements into one HDF5 file)

    device.hdf5_disable()
    
    device.deinitialize()

if __name__ == "__main__":
    test_hdf5_streaming()
