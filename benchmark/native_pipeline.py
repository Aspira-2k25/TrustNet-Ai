"""Resumable CPU research with development-only selection before sealed testing.

Default to CommunityForensics + DINO. A full OpenCLIP extraction is considered
only if development recall does not improve and the source-shortcut audit passes.
No automatic deployment. All source files and feature caches remain external.
"""
import argparse,json,os,subprocess,sys,time
from pathlib import Path


def development_rank(head):
    choice=head['choice']
    return (choice['selection_recall'],-choice['selection_real_fpr'],-len(head['backbones']))


def needs_openclip(head):
    auc=head.get('original_metadata_shortcut_auc')
    return (auc is not None and abs(auc-.5)<=.05 and
            head['choice']['selection_recall']<=head['development_primary']['selection_recall'])


def terminate_owned(process):
    if process.poll() is not None:return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    else:process.terminate()
    process.wait(timeout=15)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--holdout',type=Path,required=True);p.add_argument('--threads',type=int,default=2)
    p.add_argument('--backbones',nargs='+',choices=['community','dino','openclip'],default=['community','dino'])
    a=p.parse_args();root=Path(__file__).resolve().parents[1];out=a.output.resolve();source=a.source.resolve();holdout=a.holdout.resolve()
    if out.is_relative_to(root):raise ValueError('Keep research data outside runtime repository')
    if not 1<=a.threads<=8 or len(set(a.backbones))!=len(a.backbones):raise ValueError('Invalid CPU or backbone configuration')
    out.mkdir(parents=True,exist_ok=True);test_cache=out/'test-features';test_cache.mkdir(exist_ok=True)
    env={**os.environ,'HF_HUB_DISABLE_XET':'1','OMP_NUM_THREADS':str(a.threads),'MKL_NUM_THREADS':str(a.threads),'CUDA_VISIBLE_DEVICES':''}
    state=out/'pipeline-state.json';completed=[]
    def run(stage,args):
        log=out/(stage+'.log');started=time.time()
        state.write_text(json.dumps({'stage':stage,'status':'running','started_unix':started,'completed_this_run':completed,'note':'No production promotion or accuracy claim until independent evaluation and full-pipeline guard pass.'},indent=2))
        print('STAGE',stage,flush=True)
        with log.open('a',encoding='utf-8') as stream:
            process=subprocess.Popen([sys.executable,*args],cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                while process.poll() is None:
                    if time.time()-started>12*3600:raise TimeoutError('CPU stage exceeded 12-hour bound')
                    time.sleep(10)
            except BaseException:
                terminate_owned(process)
                state.write_text(json.dumps({'stage':stage,'status':'interrupted','log':log.name,'completed_this_run':completed},indent=2))
                raise
        if process.returncode:
            state.write_text(json.dumps({'stage':stage,'status':'failed','exit_code':process.returncode,'log':log.name,'completed_this_run':completed},indent=2));raise SystemExit(process.returncode)
        completed.append(stage)
    def extract(name):
        run(name+'-development',['benchmark/native_backbones.py','--source',str(source),'--output',str(out),'--backbone',name,'--threads',str(a.threads),'--augment'])
    def fit(names):
        candidate=out/('candidate-'+'-'.join(names)+'.json')
        run('fit-'+'-'.join(names),['benchmark/native_head.py','--source',str(source),'--cache',str(out),'--holdout',str(holdout),'--backbones',*names,'--candidate',str(candidate)])
        return candidate,json.loads(candidate.read_text())
    for name in a.backbones:extract(name)
    candidate,head=fit(a.backbones)
    if 'openclip' not in a.backbones:
        if needs_openclip(head):
            extract('openclip');extra,alternative=fit([*a.backbones,'openclip'])
            if development_rank(alternative)>development_rank(head):candidate,head=extra,alternative
        else:print('Skipping full OpenCLIP: no development justification or unresolved source-shortcut confound. Saved pilot features preserved.',flush=True)
    # Select once from development results. No fresh test outcome influences this.
    for name in head['backbones']:
        run(name+'-sealed-test',['benchmark/native_backbones.py','--source',str(holdout),'--output',str(test_cache),'--backbone',name,'--threads',str(a.threads),'--backbone-cache',str(out),'--sealed-candidate',str(candidate)])
    run('evaluate-frozen-head',['benchmark/native_head.py','--evaluate','--source',str(holdout),'--cache',str(test_cache),'--candidate',str(candidate)])
    state.write_text(json.dumps({'status':'complete','completed_this_run':completed,'selected_candidate':candidate.name,'deployed':False,'report':'test-features/holdout-report.json','note':'AI-stream diagnostic only. Source confounds, full-pipeline guard, runtime parity and artifact installation remain required before promotion.'},indent=2))
    print('CPU RESEARCH COMPLETE; production unchanged',flush=True)


if __name__=='__main__':main()
