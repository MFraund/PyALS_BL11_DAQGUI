# -*- coding: utf-8 -*-
"""
Created on Sun Nov 21 17:11:57 2021

@author: admin
"""
#%% Imports
import numpy as np


#%% Deviation values measured as xraycenter - lasercenter
horizontal_deviation = 19
vertical_deviation = -26














########### Leave this alone ########

#%% Calibrated manipulator-to-picomotor factors
Aspmx = 0.190
Aspmy = 0.610
Bspmx = 0.212
Bspmy = -0.256

#%% Solving Eqn

calibration_matrix = [[Aspmx, Bspmx],
                      [Aspmy, Bspmy]]

A = np.array(calibration_matrix)

deviation_matrix = [horizontal_deviation, vertical_deviation]

B = np.array(deviation_matrix)

X = np.linalg.inv(A).dot(B)
print(X)

