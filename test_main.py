from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_get_recipe():
    r = client.post(
        "/recipes",
        json={"title": "Pancakes", "ingredients": ["flour", "milk"], "tags": ["breakfast"]},
    )
    assert r.status_code == 200
    rid = r.json()["id"]
    r2 = client.get(f"/recipes/{rid}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Pancakes"
    assert r2.json()["tags"] == ["breakfast"]


def test_list_recipes():
    client.post("/recipes", json={"title": "Toast"})
    r = client.get("/recipes")
    assert r.status_code == 200
    assert any(rec["title"] == "Toast" for rec in r.json())


def test_list_recipes_filtered_by_tag():
    client.post(
        "/recipes",
        json={"title": "Tag filter breakfast target", "tags": ["breakfast"]},
    )
    client.post(
        "/recipes",
        json={"title": "Tag filter lunch", "tags": ["lunch"]},
    )

    r = client.get("/recipes", params={"tag": "breakfast"})

    assert r.status_code == 200
    recipes = r.json()
    titles = [recipe["title"] for recipe in recipes]
    assert "Tag filter breakfast target" in titles
    assert "Tag filter lunch" not in titles
    assert all("breakfast" in recipe["tags"] for recipe in recipes)


def test_unknown_recipe_404():
    r = client.get("/recipes/99999")
    assert r.status_code == 404


def test_shopping_list_merges_and_deduplicates_ingredients():
    first = client.post(
        "/recipes",
        json={"title": "First", "ingredients": ["flour", "milk", "flour"]},
    ).json()
    second = client.post(
        "/recipes",
        json={"title": "Second", "ingredients": ["milk", "eggs"]},
    ).json()

    r = client.get(f"/shopping-list?ids={first['id']},{second['id']}")

    assert r.status_code == 200
    assert r.json() == ["flour", "milk", "eggs"]


def test_shopping_list_rejects_invalid_ids():
    r = client.get("/shopping-list?ids=1,nope")

    assert r.status_code == 422


def test_shopping_list_returns_404_for_missing_recipe():
    existing = client.post(
        "/recipes",
        json={"title": "Existing", "ingredients": ["flour"]},
    ).json()

    r = client.get(f"/shopping-list?ids={existing['id']},99999")

    assert r.status_code == 404
