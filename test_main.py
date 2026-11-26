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
