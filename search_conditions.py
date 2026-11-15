import pandas as pd
import json

df = pd.read_csv('/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/Synthea-Healthcare-Analytics/Synthea_Real_Export/patient_condition.csv')
df['props'] = df['condition_properties'].apply(json.loads)
props = pd.json_normalize(df['props'])

for kw in ['diabetes','hypertension','heart','obesity','COVID','ARDS','respiratory','prediabetes','hyperlipidemia']:
    m = props[props['DESCRIPTION'].str.contains(kw, case=False, na=False)]
    if len(m)>0:
        print(kw.upper(), m['DESCRIPTION'].value_counts().to_dict())