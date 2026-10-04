"""Validation-only safety checks for the three-finger model revision."""
import numpy as np
from gesture_features import GestureGate

def revision_checks(actual, accepted, hands, kinds, groups=None, timestamps=None, runtime_labels=None):
    actual=np.asarray(actual);accepted=np.asarray(accepted)
    hands=np.asarray(hands);kinds=np.asarray(kinds)
    result={}
    for hand in ('left','right'):
        negative=(hands==hand)&(kinds=='three_finger_negative')
        v_pose=(hands==hand)&(actual=='next')&(kinds=='base_four_classes')
        result[hand]={
            'three_finger_samples':int(negative.sum()),
            'three_finger_false_commands':int(np.sum(negative & (accepted!='neutral'))),
            'v_samples':int(v_pose.sum()),
            'v_accepted':int(np.sum(v_pose & (accepted=='next'))),
        }
    temporal=groups is not None
    if temporal:
        groups=np.asarray(groups);timestamps=np.asarray(timestamps)
        runtime_labels=np.asarray(runtime_labels if runtime_labels is not None else accepted)
        for hand in ('left','right'):
            result[hand].update(three_finger_clips=0,three_finger_command_events=0,v_clips=0,v_confirmed_clips=0)
        for group in dict.fromkeys(groups.tolist()):
            mask=groups==group
            first=int(np.where(mask)[0][0]);hand=str(hands[first])
            if hand not in result:continue
            gate=GestureGate();commands=[]
            order=np.where(mask)[0]
            order=order[np.argsort(timestamps[order])]
            for i in order:
                command=gate.update(str(runtime_labels[i]),float(timestamps[i]))
                if command:commands.append(command)
            if kinds[first]=='three_finger_negative':
                result[hand]['three_finger_clips']+=1
                result[hand]['three_finger_command_events']+=len(commands)
            elif actual[first]=='next':
                result[hand]['v_clips']+=1
                result[hand]['v_confirmed_clips']+=int(commands==['next'])
    # Temporal checks match the unchanged live gate; frame errors remain reported.

    if temporal:
        passed=all(r['three_finger_clips']>0 and r['three_finger_command_events']==0
                   and r['v_clips']>0 and r['v_confirmed_clips']==r['v_clips']
                   and r['v_samples']>0 and r['v_accepted']/r['v_samples']>=0.95
                   for r in result.values())
        rule='zero three-finger command events through the unchanged gate, exactly one next per V clip, and >=95% V frame recall per hand'
    else:
        passed=all(r['three_finger_samples']>0 and r['three_finger_false_commands']==0
                   and r['v_samples']>0 and r['v_accepted']/r['v_samples']>=0.95
                   for r in result.values())
        rule='zero three-finger false-command frames and >=95% V recall on validation for each hand'
    return {'passed':passed,'per_hand':result,'rule':rule}
