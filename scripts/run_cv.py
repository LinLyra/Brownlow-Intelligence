import sys, os
sys.path.append('src')
import pandas as pd
from brownlow.data import load_data,audit_and_clean
from brownlow.features import build_features,model_columns
from brownlow.experiment import temporal_cv,baseline_cv

df=load_data('data/raw/brownlow_datathon_dataset.csv')
hist,future,report=audit_and_clean(df)
# Build together so 2026 lagged history sees 2015-25 but never future votes.
all_clean=pd.concat([hist,future],ignore_index=True).sort_values(['match_date','match_id','player_id']).reset_index(drop=True)
feat=build_features(all_clean)
histf=feat[feat.season<2026].copy()
nums,cats=model_columns(histf); features=nums+cats
base=baseline_cv(histf)
print('\nBASELINES\n',base.to_string(index=False))
score,oof=temporal_cv(histf,features,cats)
os.makedirs('outputs/oof',exist_ok=True); os.makedirs('outputs/reports',exist_ok=True)
score.to_csv('outputs/reports/cv_scorecard.csv',index=False)
oof.to_csv('outputs/oof/oof_predictions.csv',index=False)
print('\nMODELS\n',score.to_string(index=False))
print('\nMEAN RMSE\n',score.groupby('model').rmse.mean().sort_values().to_string())
