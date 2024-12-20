from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from wordcloud import WordCloud
import pandas as pd
import json
import emoji
from flask_cors import CORS
import os
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow requests from all origins

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReviewScraper:
    def __init__(self, product_url):
        self.base_url = "https://www.flipkart.com"
        self.product_url = product_url
        self.reviews = []
        self.review_title = []
        self.ratings = []
        self.sentiments = []
        self.page_url = []
        self.analyzer = SentimentIntensityAnalyzer()

    def make_soup(self, url):
        """Get the HTML of the product review page."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching URL {url}: {e}")
            return None

    def fill_review_title(self, soup):
        """Extract the review title from the page."""
        for title in soup.find_all('p', class_='z9E0IG'):
            self.review_title.append(title.text)

    def fill_reviews(self, soup):
        """Extract the review text."""
        for review in soup.find_all('div', class_='ZmyHeo'):
            self.reviews.append(review.text.replace('READ MORE', '').strip())

    def fill_ratings(self, soup):
        """Extract the ratings for each review."""
        for star in soup.find_all('div', class_='XQDdHH Ga3i8K'):
            self.ratings.append(star.text.strip())

    def fetch_reviews(self):
        """Fetch reviews from the product page."""
        soup = self.make_soup(self.product_url)
        if not soup:
            return

        # Fetch all review page links
        for links in soup.find_all('a', class_='cn++Ap'):
            self.page_url.append(self.base_url + links['href'])

        # Scrape reviews from all review pages
        for url in self.page_url:
            soup = self.make_soup(url)
            if soup:
                self.fill_ratings(soup)
                self.fill_review_title(soup)
                self.fill_reviews(soup)

    def analyze_sentiment(self):
        """Analyze sentiment of each review."""
        for review in self.reviews:
            cleaned_review = emoji.demojize(review)  # Remove emojis
            score = self.analyzer.polarity_scores(cleaned_review)
            compound_score = score['compound']
            
            if compound_score >= 0.05:
                sentiment = "positive"
            elif compound_score <= -0.05:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            self.sentiments.append(sentiment)

    def get_wordcloud_data(self):
        """Generate data for a word cloud."""
        text = " ".join(self.reviews)
        # Remove emojis for cleaner word cloud text
        text = emoji.replace_emoji(text, "")
        return text

    def get_sentiment_distribution(self):
        """Get sentiment distribution data."""
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for sentiment in self.sentiments:
            sentiment_counts[sentiment] += 1
        return sentiment_counts

    def get_rating_distribution(self):
        """Get rating distribution data."""
        rating_counts = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        for rating in self.ratings:
            if rating in rating_counts:
                rating_counts[rating] += 1
        return rating_counts

@app.route("/scrape_reviews", methods=["POST"])
def scrape_reviews():
    """Handle the review scraping and sentiment analysis."""
    content = request.get_json()
    product_url = content.get('url')

    if not product_url:
        return jsonify({"error": "URL is required"}), 400

    scraper = ReviewScraper(product_url)
    scraper.fetch_reviews()

    if not scraper.reviews:
        return jsonify({"error": "Failed to fetch reviews. Please check the URL."}), 500

    scraper.analyze_sentiment()

    # Prepare data for the frontend
    wordcloud_text = scraper.get_wordcloud_data()
    sentiment_distribution = scraper.get_sentiment_distribution()
    rating_distribution = scraper.get_rating_distribution()

    return jsonify({
        "message": "Scraping and analysis completed successfully!",
        "reviews_scraped": len(scraper.reviews),
        "wordcloud_text": wordcloud_text,
        "sentiment_distribution": sentiment_distribution,
        "rating_distribution": rating_distribution
    })

if __name__ == "__main__":
    # Use Render's PORT environment variable if available
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
