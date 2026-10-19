"""Durable first-completion-wins ledger and detector-result store in MongoDB."""
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

class ResultRepository:
    def __init__(self, uri, database="trustnet"):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, socketTimeoutMS=5000, retryWrites=True)
        self.collection = self.client[database]["phishing_results"]
    def ping(self):
        self.client.admin.command("ping")
    def get(self, scan_id, fingerprint):
        saved = self.collection.find_one({"_id": scan_id})
        if saved and saved["request_fingerprint"] != fingerprint:
            raise ValueError("Conflicting request for the same phishing scan")
        return saved["completion"] if saved else None
    def save(self, scan_id, fingerprint, completion):
        try:
            self.collection.insert_one({"_id": scan_id, "request_fingerprint": fingerprint, "completion": completion})
        except DuplicateKeyError:
            pass
        return self.get(scan_id, fingerprint)
    def close(self):
        self.client.close()
