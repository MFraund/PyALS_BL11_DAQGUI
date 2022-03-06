from epics import caget, cainfo, PV

cainfo('MOCounter:FREQUENCY')
cainfo('SR:BCM:BunchQ')


import pandas as pd
from epics import PV

bq = PV('SR:BCM:BunchQ')
freq = PV('MOCounter:FREQUENCY')


def cb(**kw): 
    bunchq.append('charge', 
                  pd.Series(kw['value'], name=kw['timestamp']
                            ).to_frame().T
                  )
bunchq = pd.HDFStore("charges.h5")
bq.add_callback(cb)

bunchq.charge
