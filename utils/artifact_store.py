import json
import copy
import uuid
import hashlib
from typing import Any
from threading import Lock
from collections import defaultdict


class ArtifactStore:
    def __init__(self):
        self._artifacts: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self._lock = Lock()

    def get(self, run_id, artifact_id):
        try:
            with self._lock:
                return copy.deepcopy(self._artifacts[run_id][artifact_id])
        except KeyError:
            raise KeyError(f"Artifact '{artifact_id}' 不存在或不属于当前 run")

    def put(self, run_id: str, data: str, producer: str) -> str:
        artifact_id = f"art_{uuid.uuid4().hex}"
        digest = hashlib.sha256(data.encode("utf-8")).hexdigest()

        artifact = {
            "artifact_id": artifact_id,
            "producer": producer,
            "digest": digest,
            "data": data,
        }

        with self._lock:
            self._artifacts[run_id][artifact_id] = artifact

        return artifact_id
