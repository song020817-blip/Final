import joblib

models = joblib.load("real_estate_model_simple.pkl")

key = list(models.keys())[0]
value = models[key]

print("KEY:", key)
print("VALUE TYPE:", type(value))
print("VALUE LENGTH:", len(value))

for i, v in enumerate(value):
    print(f"[{i}] type =", type(v))
