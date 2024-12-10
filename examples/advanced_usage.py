"""
Advanced usage example showing more sophisticated features and integrations.
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from knowledge_base_explorer.ingestion import ContentProcessor, BatchProcessor
from knowledge_base_explorer.nlp import ContentCategorizer, SemanticSearch
from knowledge_base_explorer.recommendation import (
    RecommendationEngine,
    PersonalizationManager,
    DiscoveryEngine
)
from knowledge_base_explorer.storage import Database, ContentIndex
from knowledge_base_explorer.utils.config import load_config
from knowledge_base_explorer.utils.logger import setup_logger

async def advanced_demo():
    # Setup logging
    logger = setup_logger()
    logger.info("Starting advanced demo")
    
    # Load configuration
    config = load_config()
    
    # Initialize components with advanced settings
    db = Database(
        connection_string=config["database_url"],
        enable_caching=True,
        max_connections=5
    )
    
    content_index = ContentIndex(
        index_path=config["index_path"],
        similarity_threshold=0.75
    )
    
    processor = BatchProcessor(
        config=config,
        parallel_processing=True,
        max_workers=3
    )
    
    categorizer = ContentCategorizer(model_path=config["nlp_model_path"])
    semantic_search = SemanticSearch(embedding_model=config["embedding_model"])
    
    recommender = RecommendationEngine(config=config)
    personalizer = PersonalizationManager(user_data_path=config["user_data_path"])
    discovery_engine = DiscoveryEngine(
        novelty_threshold=0.6,
        diversity_weight=0.3
    )
    
    # 1. Batch process multiple content sources
    content_paths = [
        Path("./sample_data/articles/"),
        Path("./sample_data/videos/")
    ]
    processed_contents = await processor.process_batch(content_paths)
    
    # Store and index content
    for content in processed_contents:
        content_id = await db.store_content(content)
        await content_index.index_content(content_id, content)
    
    # 2. Demonstrate advanced search capabilities
    search_query = {
        "keywords": ["AI product management"],
        "categories": ["technical", "strategy"],
        "date_range": {
            "start": datetime.now() - timedelta(days=30),
            "end": datetime.now()
        },
        "semantic_similarity": True
    }
    
    search_results = await semantic_search.search(
        query=search_query,
        top_k=5,
        min_similarity=0.7
    )
    
    # 3. Generate personalized recommendations with discovery
    user_id = "user123"
    user_profile = await personalizer.get_user_profile(user_id)
    
    # Get standard recommendations
    recommendations = await recommender.get_recommendations(
        user_id=user_id,
        user_profile=user_profile,
        n_recommendations=5
    )
    
    # Enhance with serendipitous discoveries
    discoveries = await discovery_engine.find_novel_content(
        user_profile=user_profile,
        recent_interactions=await db.get_user_interactions(user_id),
        n_discoveries=3
    )
    
    # 4. Analyze content relationships
    content_id = recommendations[0]["content_id"]
    related_content = await content_index.find_related_content(
        content_id=content_id,
        relationship_types=["semantic", "categorical", "citation"],
        max_results=5
    )
    
    # 5. Generate insights
    topic_trends = await analyzer.analyze_topic_trends(
        timeframe=timedelta(days=30),
        min_occurrence=5
    )
    
    emerging_topics = await analyzer.identify_emerging_topics(
        baseline_period=timedelta(days=90),
        analysis_period=timedelta(days=30)
    )
    
    # Print results
    print("\nAdvanced Search Results:")
    for result in search_results:
        print(f"- {result['title']} (Similarity: {result['similarity']:.2f})")
    
    print("\nPersonalized Recommendations:")
    for rec in recommendations:
        print(f"- {rec['title']} (Score: {rec['score']:.2f})")
    
    print("\nSerendipitous Discoveries:")
    for disc in discoveries:
        print(f"- {disc['title']} (Novelty: {disc['novelty_score']:.2f})")
    
    print("\nEmerging Topics:")
    for topic in emerging_topics:
        print(f"- {topic['name']} (Growth Rate: {topic['growth_rate']:.2f})")

if __name__ == "__main__":
    asyncio.run(advanced_demo())
