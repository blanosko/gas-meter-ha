# Table of Contents
- [Table of Contents](#table-of-contents)
- [Synopsis](#synopsis)
- [Script differences](#script-differences)
    - [Original code by andr2000](#original-code-by-andr2000)
    - [My reworked code](#my-reworked-code)
    - [Considerations](#considerations)
- [Code Usage](#code-usage)
  - [Prerequisites](#prerequisites)
    - [Software/Hardware](#softwarehardware)
    - [Meter Readings File Structure](#meter-readings-file-structure)
    - [Zeroing Energy Counters of Your Boiler](#zeroing-energy-counters-of-your-boiler)
  - [Taking The Readings](#taking-the-readings)
  - [Running the Script](#running-the-script)
    - [OPTIONAL: Template sensor YAML generation](#optional-template-sensor-yaml-generation)
- [Accuracy of the model](#accuracy-of-the-model)
- [Code explanation](#code-explanation)
    - [Step-by-Step](#step-by-step)
  - [Math and output values explanations](#math-and-output-values-explanations)
    - ["Simple" by ChatGPT](#simple-by-chatgpt)
    - [Intercept and coefficients](#intercept-and-coefficients)
    - [R values](#r-values)
    - [Error values (MAE and RMSE)](#error-values-mae-and-rmse)


# Synopsis
This project draws significant inspiration from andr2000, techniczny, and Bee Guan Teo. Without their contributions this work wouldn't exist. I've undertaken a modernization effort, simplifying the original script and providing comprehensive documentation for seamless integration with Home Assistant.

For a deeper understanding, I referenced the following links:
- [andr2000's original script](https://github.com/andr2000/ufh-controller/blob/872a2783040d9da02c5a526eea54a5c14f791468/gas_meter/meter_readings.py)
- [Techniczny's blog post on gas consumption measurement with Raspberry Pi and Ebus](https://techniczny.wordpress.com/2018/04/08/pomiar-zuzycia-gazu-przez-raspberry-pi-i-ebus/)
- [Bee Guan Teo's guide on multiple linear regression with scikit-learn library](https://medium.com/ds-notes/multiple-linear-regression-with-scikit-learn-a-quickstart-guide-41a310bd8414)
- [john30's ebusd github](https://github.com/john30/ebusd)
- [Understanding the significance of setting a random state in machine learning models](https://towardsdatascience.com/why-do-we-set-a-random-state-in-machine-learning-models-bb2dc68d8431)

# Script differences

### Original code by andr2000
  - **Library Used:** Directly uses NumPy for computing the least squares solution (`np.linalg.lstsq`). Not easily configurable.
  - **Data Manipulation:** Processes data directly from a CSV file using basic Python code without Pandas.
  - **Features:** Simpler and more concise without the use of functions. Performs calculations and prints results directly.

### My reworked code
  - **Library Used:** Uses scikit-learn's `LinearRegression` for the multiple linear regression model. Configurable.
  - **Data Manipulation:** Uses Pandas for data manipulation.
  - **Features:** Not only performs predictions but also provides valuable metrics for evaluating the model's performance. Provides a more structured approach with functions and separate sections for data loading, model fitting, and evaluation. Also eliminates all `for` loops from the original code.

### Considerations
Both scripts achieve the same task of performing multiple linear regression on meter readings data, but they use slightly different approaches and libraries. The choice between them depends on your preferences. Here are some considerations for each:

- If you prefer a more structured and modular code with the use of a well-established machine learning library (scikit-learn) and additional data manipulation and analysis beyond linear regression (e.g., extensive data cleaning, exploration, or visualization), the `gas-meter-estimation.py` might be a better choice.

- If you prefer a simpler and more direct approach, especially for smaller datasets and basic linear regression, the `original code by andr2000` script could be more suitable.



# Code Usage
All of the following chapters explain how to use the `gas-meter-estimation.py` code.

## Prerequisites
### Software/Hardware
This guide assumes that you already have:
  - A boiler that has support for the EBUS protocol.
  - A boiler that is the sole consumer of gas in your household.
  - Home Assistant running in a VM, container, or bare metal.
  - EBUSD running in a VM or container.
  - MQTT broker running in a VM or as an add-on in Home Assistant.
  - EBUSD correctly configured, and you are able to successfully read data from the EBUS adapter of your choice.
  - EBUSD is sending data periodically to the MQTT broker, and Home Assistant can read it.
  - Sensor entities for `PrEnergySumHc1` and `PrEnergySumHwc1` configured in Home Assistant.

Additionally, you will need to have VSCode and Python installed on your computer. Also, you should install the non-built-in libraries with pip:

```bash
pip install pandas
pip install numpy
pip install sklearn-scikit
```
---
### Meter Readings File Structure
Before you can leverage the script, you need to populate a `meter_readings.csv` file with real-world data from your gas meter and `PrEnergySumHc1` and `PrEnergySumHwc1` sensor values. **Delete all rows in `meter_readings.csv` but leave the headers intact before taking your readings**. 

The CSV file should have these headers:
  - **FIELD_DATETIME** - STRING - Date and time values when the reading was gathered (e.g., timestamp from a photo of the meter), formatting of the date or time does not matter. It is for your reference only.
  - **FIELD_METER** - FLOAT - Actual value of the gas meter (e.g., 24633.542).
  - **FIELD_HC** - INT - Value of a `PrEnergySumHc1` from the boiler at the time when you captured the actual gas meter value.
  - **FIELD_HWC** - INT - Value of a `PrEnergySumHwc1` from the boiler at the time when you captured the actual gas meter value.
  - **FIELD_VALID** - INT - Could be either `0` or `1`. This value defines if the rows' values are used in linear regression model calculations or not.
  - **FIELD_COMMENT** - STRING - Here you can comment on the row to your liking, just for your reference only.
---
### Zeroing Energy Counters of Your Boiler
It's a good idea to zero the energy counters of the boiler because it is possible that your boiler has already maxed out the value of `PrEnergySumHc1`, and the value will not go higher anymore (this was my case as the boiler was running for 3 years prior to this). You can check the value of `PrEnergySumHc1`, and if it's around 4294967238, you need to reset the energy counters of the boiler. You can do this by writing zeros to the registers with these commands from the EBUSD VM/container:

```bash
ebusctl w -c bai PrEnergySumHc1 0
ebusctl w -c bai PrEnergySumHwc1 0
ebusctl w -c bai PrEnergyCountHc1 0
ebusctl w -c bai PrEnergyCountHwc1 0
```

If the writing was successful, you should get a `done` message. You can verify if the counters were zeroed with read commands:

```bash
ebusctl r PrEnergySumHc1
ebusctl r PrEnergySumHwc1
ebusctl r PrEnergyCountHc1
ebusctl r PrEnergyCountHwc1
```

## Taking The Readings
Repeat these steps for several days (at least a week, 2-5 times per day) to have a sufficient amount of training and test data for the linear regression model to work accurately.

1. Go to your gas meter and take a picture of the value.
2. Go to Home Assistant's entities page, find entities for `PrEnergySumHc1` and `PrEnergySumHwc1` sensors, and take note of the values closest to the time of the timestamp of the picture you took in step 1.
3. Write the values to the corresponding headers in the `meter_readings.csv` file. Example:

```csv
FIELD_DATETIME,FIELD_METER,FIELD_HC,FIELD_HWC,FIELD_VALID,FIELD_COMMENT
09-01-2023 22:40,24616.338,19566,105508,1,initial
```

You should take the readings when the boiler is not heating water or radiators as the `PrEnergySumHc1` and `PrEnergySumHwc1` values go up really quickly.
## Running the Script
After gathering some data over the course of the week, you can test if the model accurately predicts the meter value only from `PrEnergySumHc1` and `PrEnergySumHwc1` sensor values. Your `meter_readings.csv` file should look somewhat like this:

```csv
FIELD_DATETIME,FIELD_METER,FIELD_HC,FIELD_HWC,FIELD_VALID,FIELD_COMMENT
2020-01-11 15:14:00,1843.745,1731509521,95512561,1,
2020-01-11 15:59:00,1844.765,1731651626,96217644,0,
2020-01-11 16:32:00,1845.059,1731930564,96217644,0,
2020-01-11 18:34:00,1846.496,1733035086,96401092,0,
2020-01-11 19:37:00,1847.240,1733683455,96401092,0,
2020-01-11 21:12:00,1848.412,1733683455,96401092,0,
2020-01-11 22:55:00,1849.662,1735840618,96401092,0,
2020-01-11 22:55:00,1849.662,1735840618,96401092,0,
2020-01-12 09:11:00,1855.427,1740684467,96991672,1,all off
2020-01-18 12:48:00,1886.517,1768401999,96991847,0,heater only
2020-01-19 09:08:00,1898.164,1777031197,99165785,1,all off
2020-01-26 11:41:08,1943.195,1815033838,100915634,1,
2020-02-16 08:05:56,2086.340,1936061866,106764049,0,
2020-03-01 10:26:41,2163.419,1999047800,110623588,1,
2020-03-09 09:40:28,2196.933,2023293881,115682332,1,
```

Then run the script in VSCode, and after a while, you will get output that looks like this:

```bash
Intercept: -223.3709961454128461
Coefficients: 1.1744935040401950e-06, 3.5042417206893120e-07

R^2 (Training): 0.999992876795281
R^2 (Testing): 0.9997354519103557

MAE: 1.873640
RMSE: 2.429729

    valid             datetime     meter  estimated   error      comment
0       1  2020-01-11 15:14:00  1843.745   1843.746  +0.001          NaN
1       0  2020-01-11 15:59:00  1844.765   1844.160  -0.605          NaN
2       0  2020-01-11 16:32:00  1845.059   1844.487  -0.572          NaN
3       0  2020-01-11 18:34:00  1846.496   1845.849  -0.647          NaN
5       0  2020-01-11 21:12:00  1848.412   1846.610  -1.802          NaN
6       0  2020-01-11 22:55:00  1849.662   1849.144  -0.518          NaN
7       0  2020-01-11 22:55:00  1849.662   1849.144  -0.518          NaN
8       1  2020-01-12 09:11:00  1855.427   1855.040  -0.387      all off
9       0  2020-01-18 12:48:00  1886.517   1887.594  +1.077  heater only
10      1  2020-01-19 09:08:00  1898.164   1898.491  +0.327      all off
11      1  2020-01-26 11:41:08  1943.195   1943.738  +0.543          NaN
12      0  2020-02-16 08:05:56  2086.340   2087.934  +1.594          NaN
13      1  2020-03-01 10:26:41  2163.419   2163.263  -0.156          NaN
14      1  2020-03-09 09:40:28  2196.933   2193.512  -3.421          NaN
```

Then take the values of `Intercept` and `Coefficients` and paste them into the corresponding variables in the template sensor value:

```yaml
template:
  - sensor:
      - name: "Estimated gas consumption"
        device_class: gas
        state_class: total
        unit_of_measurement: "m³"
        state: >
          {% set HC = states('sensor.boiler_prenergysumhc1') | int %}
          {% set HWC = states('sensor.boiler_prenergysumhwc1') | int %}
          {% set INTERCEPT = <ENTER INTERCEPT VALUE HERE> %}
          {% set COEF_1 = <ENTER COEFFICIENT 1 VALUE HERE> %}
          {% set COEF_2 = <ENTER COEFFICIENT 2 VALUE HERE> %}
          {{ (INTERCEPT + HC * COEF_1 + HWC * COEF_2) | round(3) }}
```

After importing this YAML config to `configuration.yaml` restart your Home Assistant instance, and you should find the new entity with name `sensor.estimated_gas_consumption` with an accurately estimated value of the gas meter. You could then add this entity in `Energy Dashboard` as gas consumption sensor.

**If you can't select the entity in energy dashboard there could be some statistics errors present. Go to 'Developer Tools' > 'Statistics', find the entity and click 'Fix issues'. Then it should be possible to add the entity to the energy dashboard**

And that's it!

---

### OPTIONAL: Template sensor YAML generation
It is possible to add following code to the end of the script and after you have run in it will add the calculated intercept and coefficients and generate a YAML for you that you can directly use in Home Assistants configuration.yaml:
```python
from string import Template
t = Template("""
sensor:
  - name: "Estimated gas consumption"
    device_class: gas
    state_class: total
    unit_of_measurement: "m³"
    state: >
      {% set HC = states('sensor.boiler_prenergysumhc1') | int %}
      {% set HWC = states('sensor.boiler_prenergysumhwc1') | int %}
      {% set INTERCEPT = $intercept %}
      {% set COEF_1 = $coef_1 %}
      {% set COEF_2 = $coef_2 %}
      {{ (INTERCEPT + HC * COEF_1 + HWC * COEF_2) | round(3) }}

""")
sensor = t.substitute({'intercept': MLR_INTERCEPT, 'coef_1': MLR_COEF_1, 'coef_2': MLR_COEF_2})

print(sensor)
```
# Accuracy of the model
[WORK IN PROGRESS]

# Code explanation
Here you can read on what steps the `gas-meter-estimation.py` script does.
### Step-by-Step
**Step 1: Import Necessary Libraries**
- Import essential libraries for data analysis and machine learning, including NumPy, Pandas and scikit-learn modules.

**Step 2: Define a Function for Testing Accuracy**
- Define a function (`test_accuracy`) to evaluate the accuracy of the model by comparing actual and estimated meter values.

**Step 3: Importing Data**
- Read data from a CSV file (`meter_readings.csv`) into a Pandas dataframe (`df`).
- Filter valid readings and create a new dataframe (`df_calc`) excluding unnecessary columns.

**Step 4: Define Features and Target Variable**
- Specify features (`X`) and the target variable (`y`) for the linear regression model.

**Step 5: Split the Data**
- Split the dataset into training and testing sets using scikit-learn's `train_test_split` function.

**Step 6: Create a Linear Regression Model**
- Instantiate a linear regression model using scikit-learn's `LinearRegression` class.
- Fit the model to the training data. More on this in [Math and output values explanation](#math-and-output-values-explanation)

**Step 7: Print Intercept and Coefficients**
- Print the intercept and coefficients of the linear regression model. This are the values you will use in Home Assistant's template sensor config.

**Step 8: Calculate and Print R^2 Values**
- Calculate and print the R^2 values for both the training and testing datasets. More on this in [Math and output values explanation](#math-and-output-values-explanation)

**Step 9: Calculate and Print Metrics**
- Calculate and print mean absolute error (MAE), mean squared error (MSE), and root mean squared error (RMSE) to evaluate model performance. More on this in [Math and output values explanation](#math-and-output-values-explanation)

**Step 10: Testing Accuracy on Meter Readings Dataframe**
- Create an empty dataframe (`df_test`) to store accuracy test results.
- Apply the `test_accuracy` function to assess the accuracy of the model on the entire dataset.

## Math and output values explanations
As math behind the actual computations using linear regression is beyond me, here are **simple** explanations by ChatGPT

### "Simple" by ChatGPT
**Linear Regression:**
Imagine you have a bunch of data points on a graph. Linear regression helps us draw a straight line that best fits these points. This line can be used to make predictions or understand relationships between variables.

**Multiple Linear Regression:**
Now, let's say we have more than one factor influencing the outcome. Multiple linear regression is like adding more dimensions to our graph. Instead of just one factor affecting the result, we have several.

**Example:**
Think about predicting a student's exam score. In simple linear regression, we might use just one factor, like the number of hours they studied. But in multiple linear regression, we could consider multiple factors like study hours, sleep hours, and the number of snacks eaten. Each factor contributes to the final exam score.

**Equation:**
The equation for a line in multiple linear regression looks like this:
\[ Y = b_0 + (b_1 \cdot X_1) + (b_2 \cdot X_2) + \ldots + (b_n \cdot X_n) \]

- \( Y \) is the predicted outcome.
- \( b_0 \) is the intercept (where the line crosses the Y-axis).
- \( b_1, b_2, \ldots, b_n \) are the coefficients that tell us how much each factor (\( X_1, X_2, \ldots, X_n \)) influences the outcome.

**In Simple Terms:**
Multiple linear regression helps us understand how different factors work together to affect something. It's like figuring out the recipe for success in a complex situation, considering multiple ingredients instead of just one.

### Intercept and coefficients
In the given script, the intercept and coefficients are related to the linear regression model. Here's what they represent:

1. **Intercept (`model.intercept_`):**
   - The intercept represents the predicted value of the dependent variable (target) when all independent variables (features) are set to zero.
   - In the context of the script, the intercept `MLR_INTERCEPT` is the estimated meter value when both `FIELD_HC` and `FIELD_HWC` are zero.

2. **Coefficients (`model.coef_`):**
   - Coefficients represent the change in the predicted value of the dependent variable for a one-unit change in the corresponding independent variable, holding all other variables constant.
   - In the script, `MLR_COEF_1` and `MLR_COEF_2` are the coefficients associated with `FIELD_HC` and `FIELD_HWC`, respectively.
   - For example, if `FIELD_HC` increases by one unit and all other variables remain constant, the estimated meter value would change by `MLR_COEF_1` units.

So, in the context of the script:

- `MLR_INTERCEPT`: Estimated meter value when both `FIELD_HC` and `FIELD_HWC` are zero.
- `MLR_COEF_1`: Change in the estimated meter value for a one-unit change in `FIELD_HC`, assuming `FIELD_HWC` remains constant.
- `MLR_COEF_2`: Change in the estimated meter value for a one-unit change in `FIELD_HWC`, assuming `FIELD_HC` remains constant.

These values help interpret the linear relationship between the independent variables and the predicted meter value in the context of the regression model. Keep in mind that interpretation may vary depending on the specific domain and characteristics of the dataset.

### R values
The R-squared (R^2) value is a statistical measure that represents the proportion of the variance in the dependent variable (target) that is predictable from the independent variables (features) in a regression model. In other words, it quantifies the goodness of fit of the model.

Here's what the R-squared value means:

- **R-squared value between 0 and 1:**
  - 0: The model does not explain any of the variance in the dependent variable.
  - 1: The model explains all the variance in the dependent variable.

- **R-squared value less than 0:**
  - The model is worse than a simple mean.

- **R-squared value close to 1:**
  - The model is a good fit to the data.

R-squared is often used as a measure of how well the independent variables explain the variability in the dependent variable. However, it has limitations. For example, it may not be a good indicator if the model is overfitting or if the relationships between variables are non-linear.

It's important to interpret R-squared in conjunction with other evaluation metrics and consider the specific context of the problem at hand. In regression analysis, it provides a useful but partial picture of the model's performance.

### Error values (MAE and RMSE)
1. **Mean Absolute Error (MAE):**
   - **Formula:** \( MAE = \frac{1}{n} \sum_{i=1}^{n} \left| y_{i} - \hat{y}_{i} \right| \)
   - \(n\) is the number of observations.
   - \(y_{i}\) is the actual value of the target variable for observation \(i\).
   - \(\hat{y}_{i}\) is the predicted value of the target variable for observation \(i\).
   - MAE represents the average absolute difference between the actual and predicted values. It gives equal weight to all errors.

2. **Root Mean Squared Error (RMSE):**
   - **Formula:** \( RMSE = \sqrt{\frac{1}{n} \sum_{i=1}^{n} \left( y_{i} - \hat{y}_{i} \right)^{2}} \)
   - \(n\) is the number of observations.
   - \(y_{i}\) is the actual value of the target variable for observation \(i\).
   - \(\hat{y}_{i}\) is the predicted value of the target variable for observation \(i\).
   - RMSE represents the square root of the average squared difference between the actual and predicted values. It penalizes larger errors more heavily than MAE.

In summary:

- **MAE:** It provides a measure of the average magnitude of errors. It is easier to interpret because it is in the same units as the target variable.

- **RMSE:** It provides a measure of the average size of errors, and since it squares the errors, it penalizes larger errors more. RMSE is more sensitive to outliers than MAE.

Both MAE and RMSE are useful metrics for understanding how well a regression model is performing, and the choice between them depends on the specific characteristics of the problem you are working on.
