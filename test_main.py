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


def test_scale_recipe_ingredients():
    recipe = client.post(
        "/recipes",
        json={
            "title": "Scaled recipe",
            "ingredients": ["200 g flour", "1.5 cups milk", ".5 cup sugar", "salt"],
            "tags": ["baking"],
        },
    ).json()

    r = client.get(f"/recipes/{recipe['id']}/scaled", params={"factor": "2"})

    assert r.status_code == 200
    assert r.json() == {
        "id": recipe["id"],
        "title": "Scaled recipe",
        "ingredients": ["400 g flour", "3 cups milk", "1 cup sugar", "salt"],
        "tags": ["baking"],
    }

    original = client.get(f"/recipes/{recipe['id']}")
    assert original.json()["ingredients"] == [
        "200 g flour",
        "1.5 cups milk",
        ".5 cup sugar",
        "salt",
    ]


def test_scale_recipe_rejects_invalid_factors():
    recipe = client.post("/recipes", json={"title": "Invalid scale factor"}).json()

    for factor in ["0", "-1", "inf", "nan", "not-a-number"]:
        r = client.get(
            f"/recipes/{recipe['id']}/scaled", params={"factor": factor}
        )
        assert r.status_code == 422


def test_scale_recipe_rejects_extreme_finite_factor():
    recipe = client.post(
        "/recipes",
        json={"title": "Extreme scale factor", "ingredients": ["200 g flour"]},
    ).json()

    r = client.get(
        f"/recipes/{recipe['id']}/scaled", params={"factor": "1e999999"}
    )

    assert r.status_code == 422


def test_scale_recipe_rejects_extremely_small_factor():
    recipe = client.post(
        "/recipes",
        json={"title": "Tiny scale factor", "ingredients": ["1 g flour"]},
    ).json()

    r = client.get(
        f"/recipes/{recipe['id']}/scaled", params={"factor": "1e-999999"}
    )

    assert r.status_code == 422


def test_scale_recipe_requires_factor_and_enforces_result_size_boundary():
    recipe = client.post(
        "/recipes",
        json={"title": "Scale boundaries", "ingredients": ["1 g flour"]},
    ).json()
    url = f"/recipes/{recipe['id']}/scaled"

    missing_factor = client.get(url)
    assert missing_factor.status_code == 422

    maximum_size = client.get(url, params={"factor": "1e-998"})
    assert maximum_size.status_code == 200
    scaled_ingredient = maximum_size.json()["ingredients"][0]
    assert len(scaled_ingredient) == 1000 + len(" g flour")
    assert scaled_ingredient.startswith("0.")
    assert scaled_ingredient.endswith("1 g flour")

    oversized_result = client.get(url, params={"factor": "1e-999"})
    assert oversized_result.status_code == 422


def test_scale_recipe_returns_404_for_missing_recipe():
    r = client.get("/recipes/99999/scaled", params={"factor": "2"})

    assert r.status_code == 404
