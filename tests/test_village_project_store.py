from concurrent.futures import ThreadPoolExecutor

import pytest

from app.autonomy.village_project_store import VillageProjectStore, project_id


def test_project_revision_and_request_persist_after_reopen(tmp_path):
    path = tmp_path / "nested" / "villages.sqlite3"
    store = VillageProjectStore(path)
    project = store.ensure_project("My village")
    assert project["id"] == project_id("My village") == store.project_id("My village")
    assert project["latest_revision"] is None
    assert store.ensure_project("My village") == project
    assert store.get_project("missing") is None
    initial = store.create_revision(project["id"], "My village", None)
    assert initial["status"] == "pending" and initial["result"] is None
    store.update_revision(initial["id"], "completed", result="initial.blend")
    request = store.enqueue(project["id"], "Add weathering")
    assert request["status"] == "pending" and request["revision_id"] is None and request["error"] is None
    plan = {"polish": {"block_0_0/house1": {"weathering": 0.8}}}
    revision = store.create_revision(project["id"], "My weathered village", initial["id"], request["id"], plan=plan)
    store.update_request(request["id"], "running", revision["id"])
    store.update_revision(revision["id"], "needs_attention", result="weathered.blend", error="Render incomplete")
    store.update_request(request["id"], "needs_attention", revision["id"], error="Render incomplete")

    reopened = VillageProjectStore(path)
    assert reopened.get_project(project["id"])["latest_revision"] == revision["id"]
    assert reopened.requests(project["id"], "pending") == []
    assert reopened.requests(project["id"], "needs_attention")[0]["error"] == "Render incomplete"
    revisions = reopened.revisions(project["id"])
    assert [item["id"] for item in revisions] == [initial["id"], revision["id"]]
    assert revisions[-1]["parent_id"] == initial["id"]
    assert revisions[-1]["request_id"] == request["id"]
    assert revisions[-1]["result"] == "weathered.blend"
    assert revisions[-1]["plan"] == plan and revisions[0]["plan"] is None


def test_request_order_filters_and_project_isolation(tmp_path):
    store = VillageProjectStore(tmp_path / "villages.db")
    first = store.ensure_project("First")["id"]
    second = store.ensure_project("Second")["id"]
    requests = [store.enqueue(first, text) for text in ("More trees", "Move house", "Warmer sunlight")]
    other = store.enqueue(second, "Different project")
    store.update_request(requests[1]["id"], "unsupported", error="Unknown house")
    assert [item["id"] for item in store.requests(first)] == [item["id"] for item in requests]
    assert [item["text"] for item in store.requests(first, "pending")] == ["More trees", "Warmer sunlight"]
    assert store.requests(second) == [other]
    assert store.revisions(second) == []


def test_unfinished_revision_does_not_replace_latest_verified_revision(tmp_path):
    store = VillageProjectStore(tmp_path / "villages.db")
    project = store.ensure_project("Village")["id"]
    initial = store.create_revision(project, "Initial", None)
    store.update_revision(initial["id"], "completed", "initial.blend")
    revision = store.create_revision(project, "More detail", initial["id"])
    for status in ("running", "failed"):
        store.update_revision(revision["id"], status, error="Temporary failure")
        assert store.get_project(project)["latest_revision"] == initial["id"]
    store.update_revision(revision["id"], "completed", "updated.blend")
    assert store.get_project(project)["latest_revision"] == revision["id"]
    assert store.revisions(project)[-1]["error"] is None


def test_cross_project_links_fail_without_partial_updates(tmp_path):
    store = VillageProjectStore(tmp_path / "villages.db")
    first = store.ensure_project("First")["id"]
    second = store.ensure_project("Second")["id"]
    revision = store.create_revision(first, "First", None)
    request = store.enqueue(second, "Add a tree")
    with pytest.raises(ValueError, match="another project"):
        store.create_revision(second, "Second", revision["id"])
    with pytest.raises(ValueError, match="another project"):
        store.create_revision(first, "First", None, request["id"])
    with pytest.raises(ValueError, match="another project"):
        store.update_request(request["id"], "completed", revision["id"])
    assert len(store.revisions(first)) == 1
    assert store.revisions(second) == []
    assert store.requests(second) == [request]
    with pytest.raises(ValueError, match="Unknown village project"):
        store.enqueue("unknown", "Add a tree")


def test_events_preserve_structured_payload_and_sql_text(tmp_path):
    path = tmp_path / "villages.db"
    store = VillageProjectStore(path)
    project = store.ensure_project("Village'); DROP TABLE village_projects; --")["id"]
    other = store.ensure_project("Another village")["id"]
    payload = {"request": "Make the farmer's house blue", "completed": ["wall_north"], "attempt": 2}
    event = store.append_event(project, "recovery", payload)
    store.append_event(project, "checkpoint", {"index": 3})
    reopened = VillageProjectStore(path)
    events = reopened.events(project)
    assert events[0] == event
    assert events[0]["payload"] == payload
    assert [item["kind"] for item in events] == ["recovery", "checkpoint"]
    assert reopened.events(other) == []
    assert reopened.get_project(project) is not None


def test_checkpoint_snapshot_recovery_and_project_ownership(tmp_path):
    path = tmp_path / "villages.db"
    store = VillageProjectStore(path)
    project = store.ensure_project("Village")["id"]
    other = store.ensure_project("Other")["id"]
    revision = store.create_revision(project, "Village", None)["id"]
    assert store.load_checkpoint(project, revision) is None
    store.save_checkpoint(project, revision, {"completed": [], "version": 3})
    snapshot = {"completed": [{"job": {"phase": "world"}, "artifacts": {"00000.blend": "hash"}}], "version": 3}
    store.save_checkpoint(project, revision, snapshot)
    reopened = VillageProjectStore(path)
    assert reopened.load_checkpoint(project, revision) == snapshot
    with pytest.raises(ValueError, match="another project"):
        reopened.save_checkpoint(other, revision, {"wrong": True})
    with pytest.raises(ValueError, match="another project"):
        reopened.load_checkpoint(other, revision)
    with pytest.raises(ValueError):
        reopened.save_checkpoint(project, revision, {"invalid": float("nan")})
    assert reopened.load_checkpoint(project, revision) == snapshot


def test_concurrent_cli_requests_are_not_lost(tmp_path):
    path = tmp_path / "villages.db"
    store = VillageProjectStore(path)
    project = store.ensure_project("Village")["id"]
    # Distinct store instances model a worker and independent CLI writers.
    writers = [VillageProjectStore(path) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        rows = list(executor.map(lambda i: writers[i % 4].enqueue(project, f"Update {i}"), range(20)))
    queued = store.requests(project, "pending")
    assert len(queued) == 20
    assert {row["id"] for row in queued} == {row["id"] for row in rows}
    assert [row["id"] for row in queued] == sorted(row["id"] for row in rows)


@pytest.mark.parametrize("value", ["", "  ", None, 42])
def test_blank_or_nontext_objectives_and_requests_are_rejected(tmp_path, value):
    store = VillageProjectStore(tmp_path / "villages.db")
    with pytest.raises(ValueError):
        store.ensure_project(value)
    project = store.ensure_project("Village")["id"]
    with pytest.raises(ValueError):
        store.enqueue(project, value)
