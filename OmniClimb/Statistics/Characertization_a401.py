"""
Filename: Characterization_a401.py
Author: Blaise O'Mara
Last update: 2025-06-27
Version: 1
Description:
    There are two purposes of this script. (1) To fit a curve to the a401-100 force-resistance data,
    and (2) compute the appropriate feedback resistance for the instrumentation amplifier.
"""
# %% Import necessary libary functions
import statsmodels as sm
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pandas import DataFrame, read_csv
from scipy.optimize import curve_fit
from sklearn import linear_model

# %% Load the a401-100 force-resistance trial data
df = read_csv("a401Trials.csv")
df.head()

# %% Separate force data from resistance data into arrays
M = df.to_numpy()
col = np.size(M, 1)
# force vector
f = M[:, 0]
# Resistance trials
R = M[:, 1:col]
# Flattened matrix with encoding. This makes it easier for scatterplots and curve fitting.
# You can compare one force vector with one set of values
dfm = df.melt('Force (lbsf)', var_name='Trials', value_name='vals')
dfm.head()
x = np.array(dfm["Force (lbsf)"]);
y = np.array(dfm["vals"])


# %% Fit curve to data
def power_func(x, a, b):
    return a * (x ** b)


popt, pcov = curve_fit(power_func, x, y, p0=[1, 1])
a_fit, b_fit = popt
y_fit = power_func(f, a_fit, b_fit)

# %% Plot data per trial
sns.scatterplot(data=dfm, x="Force (lbsf)", y="vals", 
                hue='Trials', palette="deep")
plt.ylabel("Resistance ($\Omega$)")
plt.xlabel("Force (lbsf)")
plt.title("A401-100 Trials")
plt.grid()
plt.legend().remove()
plt.show()

# %% Plot all the data and fitted curve
fig, axs = plt.subplots(2,1)
fig.suptitle("A401-100 Characterization: $F=523,349*R_{fs}^{-0.832}$")
axs[0].scatter(x, y, color="lightblue", marker="o", label="Observed Resistance")
axs[0].plot(f, y_fit, color="dodgerblue", label="Curve of Best Fit")
axs[0].set(title="Linear Scale", xlabel="Force (lbsf)", ylabel="Resistance ($\Omega$)")
axs[0].grid()
axs[0].legend()

axs[1].scatter(x, y, color="lightblue", marker="o", label="Observed Resistance")
axs[1].plot(f, y_fit, color="dodgerblue", label="Curve of Best Fit")
axs[1].set(yscale='log', xscale='log')
axs[1].set(title="Log Scale", xlabel="Force (lbsf)", ylabel="Resistance ($\Omega$)")
axs[1].grid()
axs[1].legend()
fig.tight_layout()
plt.show()
# %% Print the Best Fit Equation
print(f"F = {a_fit:.3f} * R_fs^({b_fit:0.3})")

# %% What about the feedback resistance? It should be constant
V_ref = 0.01
V_out = np.linspace(0, 3.3, 30)
R_f = y_fit * (V_out/V_ref)

plt.plot(y_fit, R_f, label="$R_f$")
plt.ylabel("Feedback Resistance ($\Omega$)")
plt.xlabel("FSR Resistance ($\Omega$)")
plt.title("A401-100 Characterization")
plt.grid()
plt.legend()
plt.show()

# %%
