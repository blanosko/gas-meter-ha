# Step 1: Import necessary libraries
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Step 2: Define a function for testing accuracy
def test_accuracy(row):
    # estimated_meter_value = model_intercept + HC * model_coefficient_1 + HWC * model_coefficient_2
    emv = (model.intercept_ + row["FIELD_HC"] * model.coef_[0] + row["FIELD_HWC"] * model.coef_[1])
    df_test.loc[len(df_test)] = {
        "valid": row["FIELD_VALID"],
        "datetime": row["FIELD_DATETIME"],
        "meter": row["FIELD_METER"],
        "estimated": round(emv, 3),
        "error": "{:+.3f}".format(emv - row["FIELD_METER"]),
        "comment": row["FIELD_COMMENT"],
    }

# Step 3: Importing data
df = pd.read_csv("meter_readings.csv")
df_calc = df.copy()
df_calc = df_calc.loc[df_calc["FIELD_VALID"] == 1]
df_calc.drop("FIELD_DATETIME", inplace=True, axis=1)
df_calc.drop("FIELD_VALID", inplace=True, axis=1)
df_calc.drop("FIELD_COMMENT", inplace=True, axis=1)

# Step 4: Define features (X) and target variable (y)
X = df_calc[["FIELD_HC", "FIELD_HWC"]]
y = df_calc["FIELD_METER"]

# Step 5: Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=0
)

# Step 6: Create a linear regression model and fit it to the training data
model = LinearRegression()
model.fit(X_train, y_train)
test_predictions = model.predict(X_test)

# Step 7: Print intercept and coefficients of the linear regression model
MLR_INTERCEPT = "{:.16f}".format(model.intercept_)
MLR_COEF_1 = "{:.16e}".format(model.coef_[0])
MLR_COEF_2 = "{:.16e}".format(model.coef_[1])
print(f"Intercept: {MLR_INTERCEPT}")
print(f"Coefficients: {MLR_COEF_1}, {MLR_COEF_2}\n")

# Step 8: Calculate and print the R^2 values
train_r2 = model.score(X_train, y_train)
test_r2 = model.score(X_test, y_test)
print(f"R^2 (Training): {train_r2}")
print(f"R^2 (Testing): {test_r2}\n")

# Step 9: Calculate and print mean absolute error, mean squared error, and root mean squared error
MAE = mean_absolute_error(y_test, test_predictions)
MSE = mean_squared_error(y_test, test_predictions)
RMSE = np.sqrt(MSE)
print("MAE: %f" % (MAE))
print("RMSE: %f\n" % (RMSE))

# Step 10: Testing calculated coefficients accuracy on meter readings dataframe
df_test = pd.DataFrame(columns=["valid", "datetime", "meter", "estimated", "error", "comment"])
df.apply(test_accuracy, axis=1)
print(df_test)