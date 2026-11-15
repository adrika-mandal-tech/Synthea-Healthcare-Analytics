import pandas as pd
import json

# Read patient_condition.csv and parse properties
df = pd.read_csv('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export/patient_condition.csv')
print("Patient-Condition shape:", df.shape)
print("Columns:", df.columns.tolist())
print()
print(df.head(10))
print()
print("Unique relationships:", df['relationship'].unique())

# Parse properties JSON
df['props'] = df['condition_properties'].apply(json.loads)
props_df = pd.json_normalize(df['props'])
print("\nCondition Properties columns:", props_df.columns.tolist())
print()
print(props_df.head(10))
print()
print("Unique conditions (CODE):", props_df['CODE'].nunique())
print("Unique conditions (DESCRIPTION):", props_df['DESCRIPTION'].nunique())
print()
print("Top 20 conditions:")
print(props_df['DESCRIPTION'].value_counts().head(20))