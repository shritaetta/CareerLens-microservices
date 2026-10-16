import json
import os
from typing import Any, Dict, Optional
import redis

DEFAULT_CONSTRAINTS: Dict[str, Any] = {
    "exclude_locations": [],
    "min_stipend": -1,
    "exclude_domains": [],
    "exclude_durations": [],
    "exclude_ids": [],
}


class RedisFeedbackStore:
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        redis_url: Optional[str] = None,
    ):
        self._client = redis_client
        self._redis_url = redis_url

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            url = self._redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._client = redis.Redis.from_url(url, decode_responses=True)
        return self._client

    def set_client(self, client: redis.Redis) -> None:
        """Allows injecting fakeredis or test client."""
        self._client = client

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

    def get_constraints(self, user_id: str) -> Dict[str, Any]:
        """Fetch user constraints JSON from key feedback:{user_id}."""
        key = f"feedback:{user_id}"
        try:
            raw = self.client.get(key)
        except Exception as e:
            print(f"Warning: Redis get failed for {key}: {e}")
            return {
                "exclude_locations": [],
                "min_stipend": -1,
                "exclude_domains": [],
                "exclude_durations": [],
                "exclude_ids": [],
            }

        if not raw:
            return {
                "exclude_locations": [],
                "min_stipend": -1,
                "exclude_domains": [],
                "exclude_durations": [],
                "exclude_ids": [],
            }

        try:
            data = json.loads(raw)
            # Ensure all required keys exist
            for k, default_val in DEFAULT_CONSTRAINTS.items():
                if k not in data:
                    data[k] = [] if isinstance(default_val, list) else default_val
            return data
        except Exception:
            return {
                "exclude_locations": [],
                "min_stipend": -1,
                "exclude_domains": [],
                "exclude_durations": [],
                "exclude_ids": [],
            }

    def record_feedback(
        self,
        user_id: str,
        internship_id: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Updates user constraints based on feedback reason and saves as JSON under feedback:{user_id}.
        Keeps exact constraint fields and logic from monolith.
        """
        metadata = metadata or {}
        user_constraints = self.get_constraints(user_id)

        # Process constraint based on reason
        if reason == "location_not_suitable":
            loc = metadata.get("location")
            if loc and loc not in user_constraints["exclude_locations"]:
                user_constraints["exclude_locations"].append(loc)

        elif reason == "low_stipend":
            from data_loader import parse_numeric_stipend

            current_numeric = parse_numeric_stipend(metadata.get("stipend", "0"))
            if current_numeric > user_constraints["min_stipend"]:
                user_constraints["min_stipend"] = current_numeric

        elif reason == "not_my_domain":
            dom = metadata.get("domain")
            if dom and dom not in user_constraints["exclude_domains"]:
                user_constraints["exclude_domains"].append(dom)

        elif reason == "duration_not_suitable":
            dur = metadata.get("duration")
            if dur and dur not in user_constraints["exclude_durations"]:
                user_constraints["exclude_durations"].append(dur)

        elif reason == "skills_mismatch":
            # Cannot easily skew complex embeddings dynamically, so we strictly ban this ID
            pass

        # Always ban the specific ID if they disliked it
        internship_id_str = str(internship_id)
        if internship_id_str not in user_constraints["exclude_ids"]:
            user_constraints["exclude_ids"].append(internship_id_str)

        # Persist to Redis
        try:
            self.client.set(f"feedback:{user_id}", json.dumps(user_constraints))
        except Exception as e:
            print(f"Warning: Redis set failed for feedback:{user_id}: {e}")

        return user_constraints
