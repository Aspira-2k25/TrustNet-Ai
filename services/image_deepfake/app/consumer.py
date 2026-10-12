import threading,asyncio
from shared.kafka.reliable_worker import run_worker
from services.image_deepfake.app.config.settings import settings
from services.image_deepfake.app.worker import worker
class ImageConsumerThread(threading.Thread):
    def __init__(self,bootstrap_servers=None):
        super().__init__(daemon=True,name='ImageDeepfakeKafkaConsumer')
        self.bootstrap_servers=bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self._stop_event=threading.Event()
    def run(self):
        async def predict(event):return (await asyncio.to_thread(worker.process_request,event)).payload
        asyncio.run(run_worker('image_deepfake',self.bootstrap_servers,predict,self._stop_event,settings.KAFKA_CONSUMER_GROUP))
    def stop(self):self._stop_event.set()
