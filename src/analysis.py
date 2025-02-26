import pandas as pd
from datetime import timedelta

NODOG = '강아지 없음'


def analyse_daily_activity(df: pd.DataFrame, labels=['LYING', 'SIT', 'WALK', 'FEETUP', 'BODYSHAKE']):
    df = df[df['행동'] != NODOG].copy()
    
    df['날짜-시간'] = pd.to_datetime(df['날짜'] + ' ' + df['시간'], format=r'%Y년 %m월 %d일 %H시 %M분 %S초 %f')
    df = df.sort_values(by='날짜-시간')
    
    df['기간'] = df['날짜-시간'].diff(periods=-1).abs().fillna(pd.Timedelta(seconds=0))
    
    duration_of_behavior = df.groupby('행동')['기간'].sum()
    total_duration = duration_of_behavior.sum()
    
    results = {'행동': [], '총 지속 시간': [], '비율': []}
    for behavior in labels:
        if behavior in duration_of_behavior:
            t = duration_of_behavior[behavior]
            results['행동'].append(behavior)
            results['총 지속 시간'].append(t)
            results['비율'].append(t / total_duration * 100)
        else:
            results['행동'].append(behavior)
            results['총 지속 시간'].append(timedelta(seconds=0))
            results['비율'].append(0)
    df = pd.DataFrame(results)
    return df.set_index('행동')


def analyse_total_activity(dfs: list[pd.DataFrame]):
    results = {'날짜': [], '활동량': []}
    for df in dfs:
        daily = analyse_daily_activity(df)
        results['날짜'].append(df['날짜'].iloc[0])
        results['활동량'].append(100.0 - daily['비율']['LYING'] - daily['비율']['SIT'])
    df = pd.DataFrame(results)
    df = df.sort_values('날짜')
    df['활동량 변화'] = df['활동량'].diff().fillna(0)
    df = df.reset_index()
    
    return df