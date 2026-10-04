"""Replay recorded landmark clips through the fixed live threshold and gesture gate.
This does not connect to Apple Music or choose model settings.
"""
import argparse,csv,json,sys
from pathlib import Path
import joblib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from gesture_features import features,GestureGate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model-directory',required=True)
    parser.add_argument('--session',action='append',default=[])
    parser.add_argument('--split',choices=['validation','test'],default='test')
    args=parser.parse_args()
    base=Path(__file__).resolve().parents[1]/'outputs'
    directory=base/args.model_directory
    config=json.loads((directory/'selection_frozen.json').read_text(encoding='utf-8'))
    model=joblib.load(directory/'gesture_model.joblib')
    inputs={item['file'].replace('\\','/') for item in config['inputs']}
    results=[]
    for session in sorted((base/'data'/'raw').iterdir()):
        if args.session and session.name not in args.session:continue
        for line in (session/'clips.jsonl').read_text(encoding='utf-8').splitlines():
            clip=json.loads(line)
            if not clip['accepted'] or clip['split']!=args.split:continue
            path=session/clip['csv']
            if path.relative_to(base).as_posix() not in inputs:continue
            gate=GestureGate(config['hold_seconds'],config['release_seconds'],config['max_frame_gap_seconds'])
            commands=[]
            with path.open(encoding='utf-8',newline='') as file:
                rows=list(csv.DictReader(file))
            vectors=[features([float(row[f'{axis}{i}']) for i in range(21) for axis in 'xyz'],
                              int(row['width']),int(row['height'])) for row in rows]
            probabilities=model.predict_proba(vectors)
            for row,prob in zip(rows,probabilities):
                label=str(model.classes_[prob.argmax()]) if prob.max()>=config['threshold'] else 'uncertain'
                command=gate.update(label,float(row['elapsed_seconds']))
                if command:commands.append(command)
            results.append({'session':session.name,'clip':clip['clip_id'],'actual':clip['label'],
                            'commands':commands,'false_commands':sum(c!=clip['label'] for c in commands)})
    report={'model_directory':args.model_directory,'split':args.split,'clips':results,
            'false_commands':sum(row['false_commands'] for row in results),
            'scope':'offline separate clips after release; not live gesture transitions or verified Apple Music delivery'}
    (directory/f'replay_{args.split}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
