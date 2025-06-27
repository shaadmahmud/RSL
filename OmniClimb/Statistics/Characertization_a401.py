"""
Filename: Characterization_a401.py
Author: Blaise O'Mara
Last update: 2025-06-27
Version: 1
Description:
    There are two purposes of this script. (1) To fit a curve to the a401-100 force-resistance data,
    and (2) compute the appropriate feedback resistance for the instrumentation amplifier.
"""
##
# Import necessary libary functions
import statsmodels as sm
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pandas import DataFrame, read_csv
from scipy.optimize import curve_fit
##
# Load the a401-100 force-resistance trial data
df = read_csv("a401Trials.csv")
df.head()
##
# Separate force data from resistance data
M = df.to_numpy()
col = np.size(M,1)
x = M[:, 0]
y = M[:, 1:col]
dfm = df.melt('Force (lbsf)', var_name='Trials', value_name='vals')
dfm.head()


##
# Fit curve to data
def power_func(x, a, b):
    return a * (x ** b)


popt, pcov = curve_fit(power_func, x, y, p0=[1, 1])
a_fit, b_fit = popt
y_fit = power_func(x, a_fit, b_fit)

##
# Plot all the trial data
sns.scatterplot(data=dfm, x="Force (lbsf)", y="vals", 
                hue='Trials', palette="deep")
plt.plot(x, y_fit)
plt.ylabel("Resistance ($\Omega$)")
plt.xlabel("Force (lbsf)")
plt.title("A401-100 Trials")
plt.grid()
plt.legend().remove()
plt.show()
##
