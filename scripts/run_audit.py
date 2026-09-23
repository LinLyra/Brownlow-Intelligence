import sys, json
sys.path.append('src')
from brownlow.data import load_data,audit_and_clean

df=load_data('data/raw/brownlow_datathon_dataset.csv')
hist,fut,report=audit_and_clean(df)
print(json.dumps(report,indent=2,default=str))
print('\nHistorical players/match by season:')
print(hist.groupby(['season','match_id']).size().groupby('season').value_counts().to_string())
