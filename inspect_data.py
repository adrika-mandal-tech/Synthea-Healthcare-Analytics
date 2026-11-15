import pandas as pd
import json

# Read patients.csv and parse properties
df = pd.read_csv('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export/patients.csv')
print("Patients shape:", df.shape)
print("Columns:", df.columns.tolist())
print()

# Parse properties JSON
df['props'] = df['properties'].apply(json.loads)
props_df = pd.json_normalize(df['props'])
print("Properties columns:", props_df.columns.tolist())
print()
print(props_df.head())
print()
print("Dtypes:")
print(props_df.dtypes)
print()
print("Unique GENDER:", props_df['GENDER'].unique())
print("Unique RACE:", props_df['RACE'].unique())
print("Unique ETHNICITY:", props_df['ETHNICITY'].unique())
print("Unique STATE:", props_df['STATE'].unique())
print("Unique MARITAL:", props_df['MARITAL'].unique() if 'MARITAL' in props_df.columns else 'N/A')