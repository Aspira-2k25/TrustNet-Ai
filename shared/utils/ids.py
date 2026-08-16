import uuid

# [PROPOSED] ID Format:
# We are generating raw UUIDv4 strings (e.g., "123e4567-e89b-12d3-a456-426614174000") without any prefixes.
# While the Master Spec showed a "scan_7a1b2c" style example, we are proposing strictly compliant 
# raw UUIDs here. This is because the DetectionResult contract established in AG-004 mandates that 
# scan_id is a "UUID-formatted string" and enforces it with a strict regex. 
# Adopting a prefix (e.g., "scan_<uuid>") would require a breaking change to the AG-004 contract.

def generate_request_id() -> str:
    return str(uuid.uuid4())

def generate_scan_id() -> str:
    return str(uuid.uuid4())

def generate_event_id() -> str:
    return str(uuid.uuid4())
