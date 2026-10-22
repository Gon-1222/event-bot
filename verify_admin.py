import sys, os, io, json
sys.path.insert(0,'.test-deps')
import main as m
from types import SimpleNamespace
store={}
m.list_blobs=lambda prefix:[SimpleNamespace(url=k) for k in store if k.startswith(prefix)]
m.blob_client.put=lambda path,body,**kw:store.__setitem__(path,body)
m.blob_client.delete=lambda url:store.pop(url)
m.urlopen=lambda url,**kw:io.BytesIO(store[url])
c=m.app.test_client(); base='/'+m.ADMIN_PATH; h={'X-Admin-Request':'1'}
assert c.get(base).status_code==200
assert c.post(base+'/api/toggle',json={'enabled':False}).status_code==403
assert c.post(base+'/api/toggle',json={'enabled':False},headers=h).json['enabled']==False
assert c.get('/send_random_event_to_discord').json['status']=='disabled'
r=c.post(base+'/api/events',json={'event':'test'},headers=h);assert r.status_code==201; id=r.json['id']
assert c.put(base+'/api/events/'+id,json={'event':'edited'},headers=h).status_code==200
assert c.get(base+'/api/state').json['events'][0]['event']=='edited'
assert c.delete(base+'/api/events/'+id,headers=h).status_code==200
assert c.post(base+'/api/toggle',json={'enabled':True},headers=h).json['enabled']==True
assert c.post(base+'/api/run',headers=h).status_code==503
assert c.post(base+'/api/events',json={'event':''},headers=h).status_code==400
os.environ['DISCORD_WEBHOOK_URL']='https://example.invalid'
c.post(base+'/api/events',json={'event':'send'},headers=h)
class Webhook:
    def __init__(self,**kw): pass
    def execute(self): return SimpleNamespace(status_code=204)
m.DiscordWebhook=Webhook
assert c.post(base+'/api/run',headers=h).status_code==200
assert c.get(base+'/api/state').json['events']==[]
print('PASS: page, CSRF guard, ON/OFF, disabled GET, CRUD, validation, manual send and removal (mock storage/Discord)')
