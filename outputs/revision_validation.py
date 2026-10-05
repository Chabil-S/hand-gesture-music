"""Validation-only safety checks for the three-finger model revision."""
import numpy as np
from gesture_features import GestureGate

def revision_checks(actual, accepted, hands, kinds, groups=None, timestamps=None, runtime_labels=None, *, minimum_command_recall=0.95):
    if not 0 < minimum_command_recall <= 1:
        raise ValueError('minimum_command_recall must be in (0, 1]')
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
            result[hand]['commands']={label:{'samples':int(np.sum((hands==hand)&(actual==label))),
                'accepted':int(np.sum((hands==hand)&(actual==label)&(accepted==label))),
                'clips':0,'confirmed_clips':0,'first_command_delays':[]} for label in ('toggle','next','previous')}
            neutral=(hands==hand)&(actual=='neutral')&(kinds=='base_four_classes')
            result[hand].update(neutral_samples=int(neutral.sum()),neutral_accepted=int(np.sum(neutral&(runtime_labels=='neutral'))),
                neutral_clips=0,neutral_command_events=0,release_pairs=0,release_pairs_passed=0)
        clip_orders={}
        for group in dict.fromkeys(groups.tolist()):
            mask=groups==group
            first=int(np.where(mask)[0][0]);hand=str(hands[first])
            if hand not in result:continue
            gate=GestureGate();commands=[]
            order=np.where(mask)[0]
            order=order[np.argsort(timestamps[order])]
            clip_orders[group]=order
            first_delay=None
            for i in order:
                command=gate.update(str(runtime_labels[i]),float(timestamps[i]))
                if command:
                    commands.append(command)
                    if first_delay is None:first_delay=float(timestamps[i]-timestamps[order[0]])
            if kinds[first]=='three_finger_negative':
                result[hand]['three_finger_clips']+=1
                result[hand]['three_finger_command_events']+=len(commands)
            elif actual[first]=='next':
                result[hand]['v_clips']+=1
                result[hand]['v_confirmed_clips']+=int(commands==['next'])
            if actual[first] in ('toggle','next','previous'):
                entry=result[hand]['commands'][str(actual[first])]
                entry['clips']+=1;entry['confirmed_clips']+=int(commands==[str(actual[first])])
                if first_delay is not None:entry['first_command_delays'].append(first_delay)
            elif kinds[first]=='base_four_classes' and actual[first]=='neutral':
                result[hand]['neutral_clips']+=1;result[hand]['neutral_command_events']+=len(commands)
        # Concatenate predicted command -> measured neutral -> same command.
        # These are diagnostic joins of separate clips, not real transition recordings.
        for order in clip_orders.values():
            first=order[0];hand=str(hands[first]);label=str(actual[first])
            if hand not in result or label not in ('toggle','next','previous'):continue
            for neutral_order in clip_orders.values():
                n=neutral_order[0]
                if hands[n]!=hand or actual[n]!='neutral' or kinds[n]!='base_four_classes':continue
                gate=GestureGate();commands=[];offset=0.
                for segment in (order,neutral_order,order):
                    for i in segment:
                        command=gate.update(str(runtime_labels[i]),offset+float(timestamps[i]-timestamps[segment[0]]))
                        if command:commands.append(command)
                    offset+=float(timestamps[segment[-1]]-timestamps[segment[0]])+.05
                result[hand]['release_pairs']+=1
                result[hand]['release_pairs_passed']+=int(commands==[label,label])
    # Temporal checks match the unchanged live gate; frame errors remain reported.

    if temporal:
        event_integrity_passed=all(r['three_finger_clips']>0 and r['three_finger_command_events']==0
                   and r['neutral_clips']>0 and r['neutral_command_events']==0
                   and r['neutral_samples']>0 and r['neutral_accepted']/r['neutral_samples']>=0.95
                   and r['release_pairs']>0 and r['release_pairs_passed']==r['release_pairs']
                   and all(c['clips']>0 and c['confirmed_clips']==c['clips']
                           and len(c['first_command_delays'])==c['clips'] for c in r['commands'].values())
                   for r in result.values())
        temporal_passed=event_integrity_passed and all(max(c['first_command_delays'])<=1.5
                    for r in result.values() for c in r['commands'].values())
        passed=temporal_passed and all(c['samples']>0 and c['accepted']/c['samples']>=minimum_command_recall
                    for r in result.values() for c in r['commands'].values())
        rule=f'both hands: zero three-finger/neutral command events; >={minimum_command_recall*100:g}% accepted recall per command and >=95% base neutral; exactly one correct event per command clip within 1.5s of first frame; all measured-neutral release joins produce exactly two correct commands; unchanged gate'
    else:
        passed=all(r['three_finger_samples']>0 and r['three_finger_false_commands']==0
                   and r['v_samples']>0 and r['v_accepted']/r['v_samples']>=0.95
                   for r in result.values())
        rule='zero three-finger false-command frames and >=95% V recall on validation for each hand'
    return {'passed':passed,'event_integrity_passed':event_integrity_passed if temporal else None,
            'temporal_passed':temporal_passed if temporal else None,'per_hand':result,'rule':rule,
            'minimum_command_recall':minimum_command_recall}
