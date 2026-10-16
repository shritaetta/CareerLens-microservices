import json
import pytest
from feedback_store import RedisFeedbackStore


def test_redis_feedback_store_direct_persistence(fake_redis):
    store = RedisFeedbackStore(redis_client=fake_redis)
    user_id = "test_user_42"

    # Initially empty default constraints
    initial = store.get_constraints(user_id)
    assert initial == {
        "exclude_locations": [],
        "min_stipend": -1,
        "exclude_domains": [],
        "exclude_durations": [],
        "exclude_ids": [],
    }

    # 1. Feedback for location
    store.record_feedback(
        user_id=user_id,
        internship_id="101",
        reason="location_not_suitable",
        metadata={"location": "Bangalore"},
    )

    # 2. Feedback for low stipend
    store.record_feedback(
        user_id=user_id,
        internship_id="102",
        reason="low_stipend",
        metadata={"stipend": "15000"},
    )

    # 3. Feedback for domain
    store.record_feedback(
        user_id=user_id,
        internship_id="103",
        reason="not_my_domain",
        metadata={"domain": "Marketing"},
    )

    # 4. Feedback for duration
    store.record_feedback(
        user_id=user_id,
        internship_id="104",
        reason="duration_not_suitable",
        metadata={"duration": "6 Months"},
    )

    # 5. Feedback for skills mismatch
    store.record_feedback(
        user_id=user_id,
        internship_id="105",
        reason="skills_mismatch",
    )

    # Verify Redis raw key format
    raw_redis_data = fake_redis.get(f"feedback:{user_id}")
    assert raw_redis_data is not None
    parsed = json.loads(raw_redis_data)

    assert "Bangalore" in parsed["exclude_locations"]
    assert parsed["min_stipend"] == 15000
    assert "Marketing" in parsed["exclude_domains"]
    assert "6 Months" in parsed["exclude_durations"]
    assert parsed["exclude_ids"] == ["101", "102", "103", "104", "105"]


def test_redis_feedback_endpoint_and_recommendation_exclusion(client, token_factory, fake_redis):
    user_a = "user_alpha@careerlens.local"
    user_b = "user_beta@careerlens.local"

    token_a = token_factory(user_a)
    token_b = token_factory(user_b)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Initial recommendation for User A
    resp_init = client.post(
        "/recommend",
        headers=headers_a,
        json={"skills": ["Python", "Machine Learning"], "education": "Computer Science"},
    )
    assert resp_init.status_code == 200
    init_recs = resp_init.json()
    assert len(init_recs) == 3

    disliked_internship = init_recs[0]
    disliked_id = str(disliked_internship["id"])

    # 2. User A dislikes this internship
    resp_fb = client.post(
        "/feedback",
        headers=headers_a,
        json={
            # Passed body user_id will be ignored in favor of token's sub
            "user_id": "ignored_body_user",
            "internship_id": disliked_id,
            "reason": "skills_mismatch",
            "metadata": {},
        },
    )
    assert resp_fb.status_code == 200
    fb_data = resp_fb.json()
    assert fb_data["status"] == "success"
    assert fb_data["constraints_updated"] is True
    assert disliked_id in fb_data["active_constraints"]["exclude_ids"]

    # Check that Redis has the key under user_a (not ignored_body_user)
    assert fake_redis.get("feedback:ignored_body_user") is None
    raw_user_a = fake_redis.get(f"feedback:{user_a}")
    assert raw_user_a is not None
    assert disliked_id in json.loads(raw_user_a)["exclude_ids"]

    # 3. User A requests recommendations again -> disliked_id MUST be excluded
    resp_after = client.post(
        "/recommend",
        headers=headers_a,
        json={"skills": ["Python", "Machine Learning"], "education": "Computer Science"},
    )
    assert resp_after.status_code == 200
    after_recs = resp_after.json()
    assert len(after_recs) == 3
    after_ids = [str(r["id"]) for r in after_recs]
    assert disliked_id not in after_ids

    # 4. User B requests recommendations -> disliked_id is NOT excluded for User B
    resp_b = client.post(
        "/recommend",
        headers=headers_b,
        json={"skills": ["Python", "Machine Learning"], "education": "Computer Science"},
    )
    assert resp_b.status_code == 200
    b_ids = [str(r["id"]) for r in resp_b.json()]
    assert disliked_id in b_ids
