import pandas as pd
import json

# Read patient_encounter.csv and parse properties
df = pd.read_csv('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export/patient_encounter.csv')
print("Patient-Encounter shape:", df.shape)
print("Columns:", df.columns.tolist())
print()
print("Unique relationships:", df['relationship'].unique())

# Parse properties JSON
df['props'] = df['encounter_properties'].apply(json.loads)
props_df = pd.json_normalize(df['props'])
print("\nEncounter Properties columns:", props_df.columns.tolist())
print()
print(props_df.head())
print()
print("Unique ENCOUNTERCLASS:", props_df['ENCOUNTERCLASS'].unique())
print("Unique CODE:", props_df['CODE'].nunique())
print("Unique DESCRIPTION:", props_df['DESCRIPTION'].nunique())
print()
print("ENCOUNTERCLASS distribution:")
print(props_df['ENCOUNTERCLASS'].value_counts())
print()
print("Top 20 encounter descriptions:")
print(props_df['DESCRIPTION'].value_counts().head(20))
print()
print("Date range:")
props_df['START'] = pd.to_datetime(props_df['START'])
props_df['STOP'] = pd.to_datetime(props_df['STOP'])
print("Min START:", props_df['START'].min())
print("Max START:", props_df['START'].max())
print("Min STOP:", props_df['STOP'].min())
print("Max STOP:", props_df['STOP'].max())