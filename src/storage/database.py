# src/knowledge_base_explorer/storage/database.py

########################################################
# To execute as a script and build the database 
# python src/knowledge-base-explorer/storage/database.py 
########################################################

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import Json, execute_values
import numpy as np
from pathlib import Path
from utils.logger import configure_logging

logger = configure_logging()


class Database:
    """Handles database operations for the knowledge base."""
    
    def __init__(
        self,
        connection_string: str = "postgresql://postgres:postgres@localhost:5432/knowledge_base",
        enable_caching: bool = True,
        max_connections: int = 5
    ):
        """
        Initialize database connection and ensure required setup.
        
        Args:
            connection_string: PostgreSQL connection string
            enable_caching: Whether to enable query result caching
            max_connections: Maximum number of concurrent connections
        """
        self.connection_string = connection_string
        self.enable_caching = enable_caching
        self._connection = None
        self._setup_database()
    
    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get a database connection, creating it if necessary."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(self.connection_string)
        return self._connection
    
    def _setup_database(self) -> None:
        """Set up database tables and extensions if they don't exist."""
        # First ensure the database exists
        base_conn = psycopg2.connect(
            " ".join(self.connection_string.split()[:-1] + ["dbname=postgres"])
        )
        base_conn.autocommit = True
        
        try:
            with base_conn.cursor() as cur:
                # Check if database exists
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname='knowledge_base'"
                )
                if not cur.fetchone():
                    cur.execute('CREATE DATABASE knowledge_base')
        finally:
            base_conn.close()
        
        # Now set up tables in the knowledge_base database
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Enable vector extension
                cur.execute('CREATE EXTENSION IF NOT EXISTS vector')
                
                # Create documents table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        url TEXT,
                        type TEXT,
                        timestamp BIGINT,
                        content TEXT,
                        summary TEXT,
                        embeddings vector(1536),
                        obsidian_markdown TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create keywords table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS keywords (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER REFERENCES documents(id),
                        keyword TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create necessary indexes
                cur.execute(
                    'CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type)'
                )
                cur.execute(
                    'CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword)'
                )
                cur.execute(
                    'CREATE INDEX IF NOT EXISTS idx_embeddings ON documents USING hnsw (embeddings vector_cosine_ops)'
                )
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
            conn.rollback()
            raise
    
    async def store_content(self, content: Dict[str, Any]) -> str:
        """
        Store processed content in the database.
        
        Args:
            content: Dictionary containing document data
            
        Returns:
            str: ID of the stored document
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Insert document
                cur.execute('''
                    INSERT INTO documents 
                    (url, type, timestamp, content, summary, embeddings, obsidian_markdown)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    content.get('url'),
                    content.get('type'),
                    content.get('timestamp'),
                    content.get('content'),
                    content.get('summary'),
                    content.get('embeddings'),
                    content.get('obsidian_markdown')
                ))
                
                document_id = cur.fetchone()[0]
                
                # Insert keywords if present
                if 'keywords' in content:
                    keywords_data = [
                        (document_id, keyword) 
                        for keyword in content['keywords']
                    ]
                    execute_values(
                        cur,
                        'INSERT INTO keywords (document_id, keyword) VALUES %s',
                        keywords_data
                    )
                
                conn.commit()
                return str(document_id)
                
        except Exception as e:
            logger.error(f"Error storing content: {e}")
            conn.rollback()
            raise
    
    async def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve content by ID.
        
        Args:
            content_id: Document ID to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Document data if found
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Get document
                cur.execute('''
                    SELECT 
                        id, url, type, timestamp, content, summary, 
                        embeddings, obsidian_markdown
                    FROM documents
                    WHERE id = %s
                ''', (content_id,))
                
                doc = cur.fetchone()
                if not doc:
                    return None
                
                # Get keywords
                cur.execute(
                    'SELECT keyword FROM keywords WHERE document_id = %s',
                    (content_id,)
                )
                keywords = [row[0] for row in cur.fetchall()]
                
                return {
                    'id': doc[0],
                    'url': doc[1],
                    'type': doc[2],
                    'timestamp': doc[3],
                    'content': doc[4],
                    'summary': doc[5],
                    'embeddings': doc[6],
                    'obsidian_markdown': doc[7],
                    'keywords': keywords
                }
                
        except Exception as e:
            logger.error(f"Error retrieving content: {e}")
            raise
    
    async def search_content(
        self,
        query: Dict[str, Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for content based on specified criteria.
        
        Args:
            query: Search parameters
            limit: Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: Matching documents
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                conditions = []
                params = []
                
                # Handle different query types
                if 'keywords' in query:
                    conditions.append('''
                        EXISTS (
                            SELECT 1 FROM keywords k 
                            WHERE k.document_id = d.id 
                            AND k.keyword = ANY(%s)
                        )
                    ''')
                    params.append(query['keywords'])
                
                if 'type' in query:
                    conditions.append('d.type = %s')
                    params.append(query['type'])
                
                if 'text_search' in query:
                    conditions.append('''
                        to_tsvector('english', d.content || ' ' || d.summary) @@ 
                        to_tsquery('english', %s)
                    ''')
                    params.append(query['text_search'])
                
                if 'embedding' in query:
                    conditions.append('d.embeddings <-> %s < %s')
                    params.extend([query['embedding'], query.get('similarity_threshold', 0.8)])
                
                # Construct and execute query
                base_query = '''
                    SELECT DISTINCT
                        d.id, d.url, d.type, d.timestamp, d.content, 
                        d.summary, d.embeddings, d.obsidian_markdown
                    FROM documents d
                '''
                
                where_clause = ' AND '.join(conditions) if conditions else 'TRUE'
                full_query = f"{base_query} WHERE {where_clause} LIMIT %s"
                params.append(limit)
                
                cur.execute(full_query, params)
                results = []
                
                for doc in cur.fetchall():
                    # Get keywords for each document
                    cur.execute(
                        'SELECT keyword FROM keywords WHERE document_id = %s',
                        (doc[0],)
                    )
                    keywords = [row[0] for row in cur.fetchall()]
                    
                    results.append({
                        'id': doc[0],
                        'url': doc[1],
                        'type': doc[2],
                        'timestamp': doc[3],
                        'content': doc[4],
                        'summary': doc[5],
                        'embeddings': doc[6],
                        'obsidian_markdown': doc[7],
                        'keywords': keywords
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching content: {e}")
            raise
    
    async def update_content(
        self,
        content_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update existing content in the database.
        
        Args:
            content_id: ID of document to update
            updates: Fields to update and their new values
            
        Returns:
            bool: True if successful
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Update document fields
                fields = []
                values = []
                for key, value in updates.items():
                    if key != 'keywords':
                        fields.append(f"{key} = %s")
                        values.append(value)
                
                if fields:
                    values.append(content_id)
                    query = f'''
                        UPDATE documents 
                        SET {", ".join(fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    '''
                    cur.execute(query, values)
                
                # Update keywords if present
                if 'keywords' in updates:
                    # Remove old keywords
                    cur.execute(
                        'DELETE FROM keywords WHERE document_id = %s',
                        (content_id,)
                    )
                    # Insert new keywords
                    keywords_data = [
                        (content_id, keyword) 
                        for keyword in updates['keywords']
                    ]
                    execute_values(
                        cur,
                        'INSERT INTO keywords (document_id, keyword) VALUES %s',
                        keywords_data
                    )
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating content: {e}")
            conn.rollback()
            raise
    
    async def delete_content(self, content_id: str) -> bool:
        """
        Delete content from the database.
        
        Args:
            content_id: ID of document to delete
            
        Returns:
            bool: True if successful
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Delete keywords first (due to foreign key)
                cur.execute(
                    'DELETE FROM keywords WHERE document_id = %s',
                    (content_id,)
                )
                # Delete document
                cur.execute(
                    'DELETE FROM documents WHERE id = %s',
                    (content_id,)
                )
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error deleting content: {e}")
            conn.rollback()
            raise
    
    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


async def main(data_dir: str):
    if not data_dir:
        print("Must specify a data directory")
        sys.exit(1)

    # Initialize database
    db = Database(
        connection_string="postgresql://postgres:postgres@localhost:5432/knowledge_base"
    )

    # loop through directories in data_dir
    for subdir, dirs, files in os.walk(data_dir):
        for file in files:
            file_path = os.path.join(subdir, file)
            if file_path.endswith(".json"):
                # print(os.path.join(subdir, file))
                logger.info(f"Accessed {file_path}")
                with open(file_path) as file:
                    data = json.load(file)
                content_id = await db.store_content(data)
                logger.info(f"Populated database with {content_id}")

    # # Store new content
    # content_id = await db.store_content({
    #     'url': 'https://example.com',
    #     'type': 'article',
    #     'content': 'Sample content...',
    #     'keywords': ['AI', 'ML'],
    #     'embeddings': [0.1, 0.2, ...]  # Your 1024-dim vector
    # })
    
    # # Search content
    # results = await db.search_content({
    #     'keywords': ['AI'],
    #     'text_search': 'machine learning',
    #     'type': 'article'
    # })
    
    # # Clean up
    # db.close()

##########################################################
## If run as a script, will build and populate database ##
##########################################################
if __name__ == '__main__':
    import asyncio
    data_dir = "/Users/Jeremy/Data-Science-Vault/Knowledge-base"
    asyncio.run(main(data_dir=data_dir))
