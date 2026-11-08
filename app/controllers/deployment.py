from PySide6.QtCore import QObject, QTimer

class DeploymentController(QObject):
    """UI-owned timer state machine; never runs or uploads packages."""
    def __init__(self,service):
        super().__init__(); self.service=service; self.timers=[]; self.generation=0
    def reset(self):
        self.generation+=1
        for timer in self.timers:timer.stop(); timer.deleteLater()
        self.timers=[]
    def later(self,delay,callback):
        timer=QTimer(self); timer.setSingleShot(True); timer.timeout.connect(callback); timer.start(min(delay,2147483647)); self.timers.append(timer)
    def deploy(self,release,ids,delay,stop,fail):
        s=self.service; generation=self.generation
        job={'id':f'DEP-{len(s.deployments)+1:03}','version':release.version,'targets':ids,'status':'Scheduled' if delay else 'Queued','completed':0,'when':s.now().isoformat(timespec='minutes') if not delay else f'In {delay//60000} minutes','results':{id:'Queued' for id in ids}}
        s.deployments.insert(0,job); s.log('Deployment scheduled (simulation)',job['id'],after={'targets':ids,'version':release.version}); s.changed.emit()
        def stage(index):
            if generation!=self.generation:return
            online=[id for id in ids if s.endpoint(id).online]
            for id in ids:
                if not s.endpoint(id).online:job['results'][id]='Pending — offline'
            if index<2:
                job['status']=['Downloading (simulation)','Installing (simulation)'][index]
                for id in online:job['results'][id]=job['status']
                s.changed.emit(); self.later(850,lambda:stage(index+1)); return
            failed=False
            for n,id in enumerate(online):
                e=s.endpoint(id)
                if fail and n==0: job['results'][id]='Failed (simulation)'; failed=True
                elif failed and stop:job['results'][id]='Halted'
                else:job['results'][id]='Success (simulation)'; e.agent=release.version; e.activity.append(f'Demo update to {release.version}'); job['completed']+=1
            job['status']='Halted on failure' if failed and stop else ('Completed with failure' if failed else ('Pending offline targets' if len(online)<len(ids) else 'Completed'))
            s.log('Deployment finished (simulation)',job['id'],after=job['results'],result='Failed' if failed else 'Success'); s.changed.emit()
        self.later(delay,lambda:stage(0))
