"""Validation-only safety checks for the three-finger model revision."""
import numpy as np

def revision_checks(actual, accepted, hands, kinds):
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
    # Set before new validation is inspected; no geometry veto or test tuning.
    passed=all(r['three_finger_samples']>0 and r['three_finger_false_commands']==0
               and r['v_samples']>0 and r['v_accepted']/r['v_samples']>=0.95
               for r in result.values())
    return {'passed':passed,'per_hand':result,
            'rule':'zero three-finger false-command frames and >=95% V recall on validation for each hand'}
