import pandas
import pandas as pd
from epics import PV


pv = PV('SR:BCM:BunchQ')
def cb(**kw): bunchq.append('charge', pd.Series(kw['value'], name=kw['timestamp']).to_frame().T)
bunchq = pd.HDFStore("charges.h5")
pv.add_callback(cb)
