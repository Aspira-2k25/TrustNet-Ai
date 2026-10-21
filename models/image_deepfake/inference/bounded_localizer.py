"""Resident CPU localizer with a killable request boundary.

A thread timeout cannot interrupt a native PyTorch operation. Keep the research
model in a separate, resident process; discard all partial maps on timeout.
"""
import atexit
import multiprocessing as mp
import threading
import time


def _serve(connection):
    import torch
    torch.set_num_threads(2)
    try:
        from .localizer import TruForLocalizer
        model=TruForLocalizer(time_budget=18)
        connection.send(('ready',None))
        while True:
            request=connection.recv()
            if request is None:break
            data,budget=request
            try:connection.send(('ok',model.predict(data,time_budget=budget)))
            except (ValueError,RuntimeError,MemoryError,OSError) as exc:
                connection.send(('error',str(exc)[:240]))
    except (EOFError,BrokenPipeError):pass
    except Exception as exc:
        try:connection.send(('error',type(exc).__name__+': '+str(exc)[:200]))
        except (EOFError,BrokenPipeError,OSError):pass
    finally:connection.close()


class BoundedLocalizer:
    def __init__(self,startup_timeout=30,request_timeout=20,worker=_serve):
        self.startup_timeout=startup_timeout;self.request_timeout=request_timeout
        self.worker=worker;self.lock=threading.Lock();self.process=None;self.connection=None
        self._start();atexit.register(self.close)

    def _start(self,timeout=None):
        context=mp.get_context('spawn');parent,child=context.Pipe()
        self.connection=parent;self.process=context.Process(target=self.worker,args=(child,),daemon=True)
        self.process.start();child.close()
        if not parent.poll(self.startup_timeout if timeout is None else min(timeout,self.startup_timeout)):
            self.close();raise ValueError('Edit checker could not start within its CPU budget')
        try:status,value=parent.recv()
        except (EOFError,OSError):self.close();raise ValueError('Edit checker stopped during startup')
        if status!='ready':self.close();raise ValueError('Edit checker startup failed: '+str(value))

    def close(self):
        if self.process is not None:
            if self.process.is_alive():self.process.terminate()
            self.process.join(timeout=1)
            if self.process.is_alive():self.process.kill();self.process.join(timeout=1)
        if self.connection is not None:self.connection.close()
        self.process=None;self.connection=None

    @property
    def ready(self):
        return self.process is not None and self.process.is_alive()

    def predict(self,data,time_budget=None):
        with self.lock:
            started=time.monotonic()
            if self.process is None or not self.process.is_alive():
                # Restart only for a new request, never retry the timed-out scan.
                self._start(timeout=self.request_timeout)
            budget=min(self.request_timeout,time_budget if time_budget is not None else self.request_timeout)
            budget=max(.01,budget-(time.monotonic()-started))
            try:
                self.connection.send((data,budget))
                if not self.connection.poll(budget):
                    self.close();raise ValueError('Analysis incomplete: edit checker exceeded its CPU time limit. No partial mask is returned')
                status,value=self.connection.recv()
                if status!='ok':raise ValueError(str(value))
                return value
            except (EOFError,BrokenPipeError,OSError):
                self.close();raise ValueError('Analysis incomplete: edit checker stopped. No partial mask is returned')
