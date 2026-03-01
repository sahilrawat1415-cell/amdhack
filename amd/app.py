import urllib.parse
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# Use your OpenRouter key
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

def get_direct_links(product_name, query):
    """Generates precise direct search links for the exact product name."""
    # Use the full product name for the most direct search
    exact_q = urllib.parse.quote_plus(product_name)
    search_q = urllib.parse.quote_plus(query)

    # Amazon India - direct product name search with sort by relevance
    amazon = f"https://www.amazon.in/s?k={exact_q}&ref=nb_sb_noss&s=relevancerank"

    # Flipkart - exact product search
    flipkart = f"https://www.flipkart.com/search?q={exact_q}&sort=relevance&otracker=search"

    # Google Shopping as a fallback direct link
    google_shopping = f"https://www.google.com/search?tbm=shop&q={exact_q}+buy+india"

    return {
        "amazon": amazon,
        "flipkart": flipkart,
        "google_shopping": google_shopping
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/recommend', methods=['POST'])
def recommend():
    purpose = request.form.get('purpose', '').strip()
    budget = request.form.get('budget', '').strip()
    prefs = request.form.get('preferences', '').strip()

    prompt = (
        f"You are a senior product analyst. A customer in India wants: '{purpose}'. "
        f"Budget: ₹{budget}. Extra preferences: {prefs if prefs else 'None'}. "
        "Recommend exactly 3 products. For EACH product use this exact format:\n\n"
        "ITEM_START\n"
        "NAME: [Full exact model name, e.g. Samsung Galaxy S23 FE 128GB]\n"
        "PRICE: [Approximate price in INR, e.g. ₹34,999]\n"
        "PROS: [3 key strengths, comma-separated]\n"
        "CONS: [2 main weaknesses, comma-separated]\n"
        "REVIEWS: [2-3 sentence summary of real user sentiment and common feedback]\n"
        "WHY_BUY: [Compelling 2-3 sentence justification: why this over the other 2 options? Be specific about the trade-off.]\n"
        "COMPARISON: [One line: how this compares to the other two recommendations]\n"
        "SCORE: [Rating out of 10, e.g. 8.5]\n"
        "QUERY: [Short 3-5 word search query for this exact model]\n"
        "ITEM_END\n\n"
        "Be specific, honest, and base scores on real-world value for the budget. "
        "The WHY_BUY must directly reference the other 2 products to show comparison."
    )

    try:
        completion = client.chat.completions.create(
            model="stepfun/step-3.5-flash:free",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Indian product analyst with deep knowledge of market prices, "
                        "user reviews, and value-for-money assessments. Always give exact model names "
                        "and specific, comparative reasoning. Never be vague."
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )
        ai_raw = completion.choices[0].message.content

        products = []
        for block in ai_raw.split("ITEM_START"):
            if "NAME:" not in block:
                continue
            try:
                def extract(field, next_field):
                    return block.split(f"{field}:")[1].split(f"{next_field}:")[0].strip()

                name       = extract("NAME", "PRICE")
                price      = extract("PRICE", "PROS")
                pros       = extract("PROS", "CONS")
                cons       = extract("CONS", "REVIEWS")
                reviews    = extract("REVIEWS", "WHY_BUY")
                why_buy    = extract("WHY_BUY", "COMPARISON")
                comparison = extract("COMPARISON", "SCORE")
                score      = extract("SCORE", "QUERY")
                query      = block.split("QUERY:")[1].split("ITEM_END")[0].strip()

                links = get_direct_links(name, query)
                products.append({
                    "name":        name,
                    "price":       price,
                    "pros":        [p.strip() for p in pros.split(",")],
                    "cons":        [c.strip() for c in cons.split(",")],
                    "reviews":     reviews,
                    "why_buy":     why_buy,
                    "comparison":  comparison,
                    "score":       score,
                    "amazon":      links["amazon"],
                    "flipkart":    links["flipkart"],
                    "google":      links["google_shopping"],
                })
            except (IndexError, KeyError):
                continue

    except Exception as e:
        return render_template('index.html', error=str(e))

    return render_template('index.html', products=products, purpose=purpose, budget=budget)


if __name__ == '__main__':
    app.run(debug=True)