"""One resumable CPU research command. Never changes the deployed image model.

Uses saved source files and crop feature caches. Stages run sequentially so large
backbones do not compete with each other for RAM. No GPU or paid API is used.
"""
import argparse,json,os,subprocess,sys,time
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--holdout',type=Path,required=True);p.add_argument('--threads',type=int,default=4);a=p.parse_args();root=Path(__file__).resolve().parents[1];out=a.output.resolve();source=a.source.resolve();holdout=a.holdout.resolve()
    if out.is_relative_to(root):raise ValueError('Keep research data outside runtime repository')
    out.mkdir(parents=True,exist_ok=True);test_cache=out/'test-features';test_cache.mkdir(exist_ok=True)
    stages=[]
    for name in ['community','dino','openclip']:
        stages.append((name+'-development',['benchmark/native_backbones.py','--source',str(source),'--output',str(out),'--backbone',name,'--threads',str(a.threads),'--augment']))
    stages.append(('fit-frozen-head',['benchmark/native_head.py','--source',str(source),'--cache',str(out),'--holdout',str(holdout)]))
    for name in ['community','dino','openclip']:
        stages.append((name+'-sealed-test',['benchmark/native_backbones.py','--source',str(holdout),'--output',str(test_cache),'--backbone',name,'--threads',str(a.threads),'--backbone-cache',str(out),'--sealed-candidate',str(out/'candidate.json')]))
    stages.append(('evaluate-frozen-head',['benchmark/native_head.py','--evaluate','--source',str(holdout),'--cache',str(test_cache),'--candidate',str(out/'candidate.json')]))
    env={**os.environ,'HF_HUB_DISABLE_XET':'1','OMP_NUM_THREADS':str(a.threads),'MKL_NUM_THREADS':str(a.threads),'CUDA_VISIBLE_DEVICES':''}
    state=out/'pipeline-state.json';completed=[]
    for stage,args in stages:
        log=out/(stage+'.log');started=time.time();state.write_text(json.dumps({'stage':stage,'status':'running','started_unix':started,'completed_this_run':completed,'note':'No production promotion or accuracy claim until evaluation and full-pipeline guard pass.'},indent=2))
        print('STAGE',stage,flush=True)
        with log.open('a',encoding='utf-8') as stream:
            process=subprocess.Popen([sys.executable,*args],cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                while process.poll() is None:
                    if time.time()-started>12*3600:process.terminate();raise TimeoutError('CPU stage exceeded 12-hour bound')
                    time.sleep(10)
            except BaseException:
                if process.poll() is None:process.terminate();process.wait(timeout=10)
                raise
        if process.returncode:
            state.write_text(json.dumps({'stage':stage,'status':'failed','exit_code':process.returncode,'log':str(log.name),'completed_this_run':completed},indent=2));raise SystemExit(process.returncode)
        completed.append(stage)
    state.write_text(json.dumps({'status':'complete','completed_this_run':completed,'deployed':False,'report':'test-features/holdout-report.json','note':'AI-stream report only. Full-pipeline guard, licensing and artifact installation remain required before promotion.'},indent=2));print('CPU RESEARCH COMPLETE; production unchanged',flush=True)

if __name__=='__main__':main()
