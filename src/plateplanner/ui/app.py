
from flask import Flask, render_template, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    """Display the Plate Planner dashboard."""
    return render_template("index.html")


@app.route("/recipes")
def recipes():
    """Display the recipe management page."""
    return render_template("recipes.html")


@app.route("/meal-planner")
def meal_planner():
    """Display the weekly meal planning page."""
    return render_template("meal-planner.html")


@app.route("/grocery-list")
def grocery_list():
    """Display the grocery list page."""
    return render_template("grocery-list.html")


@app.route("/nutrition")
def nutrition():
    """Display the nutrition analysis page."""
    return render_template("nutrition.html")


@app.route("/api/test")
def test_connection():
    """Test communication between the frontend and backend."""
    return jsonify({
        "message": "Successfully connected to Python!"
    })


if __name__ == "__main__":
    app.run(debug=True)
