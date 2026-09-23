import sys, os
sys.path.append('src')
import numpy as np, pandas as pd
from brownlow.data import load_data,audit_and_clean
from brownlow.features import build_features,model_columns
from brownlow.models import LGBMWrapper,CatBoostWrapper,TwoStageLGBM
from brownlow.allocation import allocate_frame

MODEL_CLASSES={'lightgbm':LGBMWrapper,'catboost':CatBoostWrapper,'two_stage':TwoStageLGBM}
MODEL_NAME='BrownlowIntelligenceV1'

df=load_data('data/raw/brownlow_datathon_dataset.csv')
hist,future,_=audit_and_clean(df)
all_clean=pd.concat([hist,future],ignore_index=True).sort_values(['match_date','match_id','player_id']).reset_index(drop=True)
feat=build_features(all_clean)
train=feat[feat.season<2026].copy(); test=feat[feat.season==2026].copy()
nums,cats=model_columns(train); features=nums+cats
# Default robust blend. Replace with OOF-optimised weights after run_cv.
weights={'lightgbm':0.40,'catboost':0.40,'two_stage':0.20}
preds=[]
for name,w in weights.items():
    m=MODEL_CLASSES[name](seed=42).fit(train[features],train.brownlow_votes,cat_cols=cats)
    preds.append(w*m.predict(test[features]))
test['raw_prediction']=np.sum(preds,axis=0)
test=allocate_frame(test,'raw_prediction','capped_simplex')

template=pd.read_csv('data/raw/submission_template_v2.csv')
keys=['season','match_round','match_home_team','match_away_team','player_id','player_first_name','player_last_name','player_team']
pred=test[keys+['prediction']].copy()
out=template.drop(columns=['brownlow_votes_prediction']).merge(pred,on=keys,how='left',validate='one_to_one')
out=out.rename(columns={'prediction':'brownlow_votes_prediction'})
assert out.brownlow_votes_prediction.notna().all()
assert out.brownlow_votes_prediction.between(0,3).all()
# Validate by fixture identity because template does not include match_id.
chk=out.groupby(['season','match_round','match_home_team','match_away_team']).brownlow_votes_prediction.sum()
assert np.allclose(chk.values,6.0,atol=1e-8), chk[(chk-6).abs()>1e-8]
os.makedirs('outputs/submissions',exist_ok=True)
path=f'outputs/submissions/Brownlow_Medal_Datathon_2026_Submission_Form_{MODEL_NAME}.csv'
out.to_csv(path,index=False)
print(path)
print('rows=',len(out),'matches=',len(chk),'sum range=',(chk.min(),chk.max()))
