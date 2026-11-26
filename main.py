"""Recipe Box — starter app for Week 8.

A tiny FastAPI service for recipes and tags, with a static frontend. Use it as the
playground for concurrent multi-agent work and a generator-critic loop.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload
    # open http://localhost:8000/
Test:
    pytest
"""
import json
import re
import sqlite3
from contextlib import closing
from decimal import Decimal, DecimalException, localcontext
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE = Path(__file__).parent
DB_PATH = BASE / "recipes.db"

app = FastAPI(title="Recipe Box")

QUANTITY_PATTERN = re.compile(r"^(\s*)((?:\d+(?:\.\d*)?|\.\d+))(\s+.+)$")
MAX_SCALED_QUANTITY_LENGTH = 1000


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS recipes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                ingredients TEXT NOT NULL,  -- JSON list of strings
                tags        TEXT NOT NULL   -- JSON list of strings
            )"""
        )
        conn.commit()


init_db()


class RecipeIn(BaseModel):
    title: str
    ingredients: list[str] = []
    tags: list[str] = []


def _row_to_recipe(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": json.loads(row["ingredients"]),
        "tags": json.loads(row["tags"]),
    }


def _scale_ingredient(ingredient: str, factor: Decimal) -> str:
    match = QUANTITY_PATTERN.match(ingredient)
    if match is None:
        return ingredient

    prefix, quantity, suffix = match.groups()
    quantity_value = Decimal(quantity)
    if (
        abs(quantity_value.adjusted()) > MAX_SCALED_QUANTITY_LENGTH
        or len(quantity_value.as_tuple().digits) > MAX_SCALED_QUANTITY_LENGTH
    ):
        raise HTTPException(status_code=422, detail="scaled ingredient quantity is too large")

    with localcontext() as context:
        context.prec = (
            len(quantity_value.as_tuple().digits) + len(factor.as_tuple().digits)
        )
        scaled_value = (quantity_value * factor).normalize()

    value_tuple = scaled_value.as_tuple()
    digit_count = len(value_tuple.digits)
    exponent = value_tuple.exponent
    adjusted = digit_count + exponent - 1
    if exponent >= 0:
        output_length = digit_count + exponent
    elif adjusted >= 0:
        output_length = digit_count + 1
    else:
        output_length = 2 + (-adjusted - 1) + digit_count
    if output_length > MAX_SCALED_QUANTITY_LENGTH:
        raise HTTPException(status_code=422, detail="scaled ingredient quantity is too large")

    scaled_quantity = format(scaled_value, "f")
    return f"{prefix}{scaled_quantity}{suffix}"


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/recipes")
def create_recipe(recipe: RecipeIn):
    with closing(get_db()) as conn:
        cur = conn.execute(
            "INSERT INTO recipes (title, ingredients, tags) VALUES (?, ?, ?)",
            (recipe.title, json.dumps(recipe.ingredients), json.dumps(recipe.tags)),
        )
        conn.commit()
        rid = cur.lastrowid
    return {"id": rid, **recipe.model_dump()}


@app.get("/recipes")
def list_recipes(tag: str | None = None):
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY id").fetchall()
    recipes = [_row_to_recipe(r) for r in rows]
    if tag is not None:
        recipes = [recipe for recipe in recipes if tag in recipe["tags"]]
    return recipes


@app.get("/shopping-list")
def shopping_list(ids: str = Query(...)):
    id_values = ids.split(",")
    if any(not value.isdigit() or int(value) <= 0 for value in id_values):
        raise HTTPException(
            status_code=422,
            detail="ids must be comma-separated positive integers",
        )
    recipe_ids = [int(value) for value in id_values]

    placeholders = ",".join("?" for _ in set(recipe_ids))
    with closing(get_db()) as conn:
        rows = conn.execute(
            f"SELECT id, ingredients FROM recipes WHERE id IN ({placeholders})",
            tuple(set(recipe_ids)),
        ).fetchall()

    recipes_by_id = {row["id"]: row for row in rows}
    missing_ids = [recipe_id for recipe_id in recipe_ids if recipe_id not in recipes_by_id]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"unknown recipe id(s): {', '.join(map(str, missing_ids))}",
        )

    ingredients = []
    seen = set()
    for recipe_id in recipe_ids:
        for ingredient in json.loads(recipes_by_id[recipe_id]["ingredients"]):
            if ingredient not in seen:
                ingredients.append(ingredient)
                seen.add(ingredient)
    return ingredients


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    with closing(get_db()) as conn:
        row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown recipe")
    return _row_to_recipe(row)


@app.get("/recipes/{recipe_id}/scaled")
def get_scaled_recipe(recipe_id: int, factor: Decimal = Query(..., gt=0)):
    if not factor.is_finite():
        raise HTTPException(status_code=422, detail="factor must be a positive finite number")
    if (
        abs(factor.adjusted()) > MAX_SCALED_QUANTITY_LENGTH
        or len(factor.as_tuple().digits) > MAX_SCALED_QUANTITY_LENGTH
    ):
        raise HTTPException(status_code=422, detail="factor is too large or small to scale safely")

    with closing(get_db()) as conn:
        row = conn.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown recipe")

    recipe = _row_to_recipe(row)
    try:
        recipe["ingredients"] = [
            _scale_ingredient(ingredient, factor)
            for ingredient in recipe["ingredients"]
        ]
    except DecimalException as exc:
        raise HTTPException(
            status_code=422, detail="factor is too large or small to scale safely"
        ) from exc
    return recipe
