"""
Basic usage example demonstrating core functionality of the knowledge base explorer.
"""
import asyncio
from pathlib import Path
from knowledge_base_explorer.ingestion import ContentProcessor
from knowledge_base_explorer.recommendation import RecommendationEngine
from knowledge_base_explorer.storage import Database
from knowledge_base_explorer.utils.config import load_config

async def basic_demo():
    # Load configuration
    config = load_config()
    
    # Initialize components
    db = Database(connection_string=config["database_url"])
    processor = ContentProcessor(config=config)
    recommender = RecommendationEngine(config=config)
    
    # 1. Ingest a single article
    article_path = Path("./sample_data/article.txt")
    processed_content = await processor.process_content(article_path)
    content_id = await db.store_content(processed_content)
    print(f"Stored article with ID: {content_id}")
    
    # 2. Get basic recommendations
    user_id = "user123"
    recommendations = await recommender.get_recommendations(
        user_id=user_id,
        n_recommendations=3
    )
    print("\nTop 3 recommended articles:")
    for rec in recommendations:
        print(f"- {rec['title']} (Score: {rec['score']:.2f})")
    
    # 3. Simple content search
    search_results = await db.search_content({
        "keywords": ["AI", "product management"],
        "max_results": 5
    })
    print("\nSearch results:")
    for result in search_results:
        print(f"- {result['title']}")

if __name__ == "__main__":
    asyncio.run(basic_demo())