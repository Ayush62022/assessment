#!/usr/bin/env python3
"""
Complete Blog Title & Metadata Suggestion System
Loads Medium dataset, processes blog markdown, and generates suggestions
"""

import pandas as pd
import sqlite3
import numpy as np
import re
import os
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import json
import traceback

# Install required packages first:
# pip install sentence-transformers pandas numpy scikit-learn python-dotenv langchain-google-genai google-generativeai

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

@dataclass
class BlogSuggestion:
    """Data class for blog suggestions"""
    titles: List[str]
    meta_description: str
    slug: str
    keywords: List[str]
    confidence: float = 0.0

class BlogSuggestionEngine:
    """Main engine for generating blog suggestions"""

    def __init__(self, dataset_path: str, db_path: str = "title_corpus.db"):
        self.dataset_path = dataset_path
        self.db_path = db_path
        self.model_name = 'all-MiniLM-L6-v2'
        self.sentence_model = None
        self.titles_df = None
        self.title_embeddings = None
        self.llm = None

        # Initialize Google GenAI
        if os.getenv("GOOGLE_API_KEY"):
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",  # Using flash for speed and cost
                    temperature=0.7,
                    max_tokens=None,
                    timeout=None,
                    max_retries=2,
                    api_key="AIzaSyAyZG81VMKg_M79VdCfEMvwMTDwv2h-yxQ"
                )
                print("✅ Google GenAI LLM Initialized.")
            except Exception as e:
                print(f"⚠️  Could not initialize Google GenAI: {e}. Falling back to heuristics.")
        else:
            print("⚠️  GOOGLE_API_KEY not found in .env file. Falling back to simple heuristics.")

        print("🚀 Initializing Blog Suggestion Engine...")
        self.load_dataset()
        self.setup_embeddings()
        self.create_database()

    def load_dataset(self):
        """Load and clean the Medium dataset"""
        print("📊 Loading Medium dataset...")
        self.titles_df = pd.read_csv(
            self.dataset_path,
            encoding='utf-8',
            quotechar='"',
            escapechar='\\',
            on_bad_lines='skip'
        )
        print(f"✅ Loaded {len(self.titles_df)} titles")
        self.titles_df = self.clean_dataset()
        print(f"🧹 After cleaning: {len(self.titles_df)} titles remain")

    def clean_dataset(self) -> pd.DataFrame:
        """Clean and prepare the dataset"""
        df = self.titles_df.copy()
        title_col = next((col for col in ['title', 'Title', 'headline', 'Headline'] if col in df.columns), None)
        if not title_col:
            raise ValueError("No title column found in dataset")
        if title_col != 'title':
            df = df.rename(columns={title_col: 'title'})
        df['title'] = df['title'].astype(str).apply(self.clean_title)
        df = df[df['title'].str.len() > 10].drop_duplicates(subset=['title'])
        if len(df) > 50000:
            df = df.sample(n=50000, random_state=42)
        return df.reset_index(drop=True)

    def clean_title(self, title: str) -> str:
        """Clean individual title"""
        if pd.isna(title): return ""
        title = re.sub(r'\s+', ' ', str(title)).strip()
        if len(title) > 120:
            title = title[:120].rsplit(' ', 1)[0] + "..."
        return title

    def setup_embeddings(self):
        """Setup sentence transformer model and create embeddings"""
        print("🤖 Loading sentence transformer model...")
        self.sentence_model = SentenceTransformer(self.model_name)
        embeddings_file = "title_embeddings.pkl"
        if os.path.exists(embeddings_file):
            print("📁 Loading cached embeddings...")
            with open(embeddings_file, 'rb') as f:
                self.title_embeddings = pickle.load(f)
        else:
            print("🔄 Creating and caching embeddings for all titles...")
            titles_list = self.titles_df['title'].tolist()
            self.title_embeddings = self.sentence_model.encode(titles_list, show_progress_bar=True)
            with open(embeddings_file, 'wb') as f:
                pickle.dump(self.title_embeddings, f)
        print(f"✅ Embeddings ready: {self.title_embeddings.shape}")

    def create_database(self):
        """Create SQLite database with titles and metadata"""
        print("🗄️ Creating SQLite database...")
        conn = sqlite3.connect(self.db_path)
        df_to_insert = self.titles_df.copy()
        df_to_insert['embedding_id'] = range(len(df_to_insert))
        for col in ['category', 'subtitle']:
            if col not in df_to_insert.columns:
                df_to_insert[col] = ''
        df_to_insert[['title', 'category', 'subtitle', 'embedding_id']].to_sql(
            'titles', conn, if_exists='replace', index=False
        )
        conn.close()
        print(f"✅ Database created with {len(df_to_insert)} titles")

    def find_similar_titles(self, query_text: str, top_k: int = 10) -> List[Tuple[str, float, str]]:
        """Find similar titles using semantic similarity"""
        query_embedding = self.sentence_model.encode([query_text])
        similarities = cosine_similarity(query_embedding, self.title_embeddings)[0]
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(
            self.titles_df.iloc[idx]['title'],
            similarities[idx],
            self.titles_df.iloc[idx].get('category', 'general')
        ) for idx in top_indices]

    def extract_keywords(self, text: str, num_keywords: int = 5) -> List[str]:
        """Extract keywords from text (simple implementation)"""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'was', 'our', 'has', 'with', 'this', 'that', 'have', 'from', 'they', 'been', 'about', 'your'}
        filtered_words = [w for w in words if w not in stop_words]
        word_freq = {word: filtered_words.count(word) for word in set(filtered_words)}
        top_keywords = sorted(word_freq, key=word_freq.get, reverse=True)
        return top_keywords[:num_keywords]

    def create_slug(self, title: str, max_tokens: int = 8) -> str:
        """Create a kebab-case slug from title"""
        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
        slug = re.sub(r'[-\s]+', '-', slug)
        return '-'.join(slug.split('-')[:max_tokens])

    def parse_llm_response(self, response_text: str) -> BlogSuggestion:
        """Parses the raw text output from the LLM into a BlogSuggestion object."""
        try:
            titles_match = re.search(r'Three catchy blog titles:.*?\n(.*?)\n\n', response_text, re.DOTALL | re.IGNORECASE)
            titles = [re.sub(r'^\d+\.\s*', '', line).strip().strip('"') for line in titles_match.group(1).strip().split('\n') if line.strip()] if titles_match else []
            
            meta_match = re.search(r'SEO meta description:.*?\n(.*?)\n\n', response_text, re.DOTALL | re.IGNORECASE)
            meta_description = meta_match.group(1).strip() if meta_match else "Meta description could not be generated."
            
            keywords_match = re.search(r'Five relevant keywords:.*?\n(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
            keywords = [k.strip() for k in re.sub(r'^\d+\.\s*-\s*', '', keywords_match.group(1), flags=re.MULTILINE).split(',')] if keywords_match else []

            if not titles: titles = ["AI Generated Title 1", "AI Generated Title 2", "AI Generated Title 3"]
            if not keywords: keywords = self.extract_keywords(response_text, 5)

            return BlogSuggestion(
                titles=titles,
                meta_description=meta_description,
                slug=self.create_slug(titles[0]),
                keywords=keywords,
                confidence=0.9
            )
        except Exception as e:
            print(f"Error parsing LLM response: {e}. Returning a fallback suggestion.")
            return BlogSuggestion(titles=["Error Parsing Response"], meta_description="", slug="error", keywords=[], confidence=0.1)

    def generate_with_llm(self, content: str, similar_titles: List[Tuple[str, float, str]]) -> BlogSuggestion:
        """Generate suggestions using the configured Google GenAI LLM."""
        title_examples = [title for title, _, _ in similar_titles[:10]]
        prompt = f"""You are an expert SEO and content marketing strategist.
        Based on the following blog content and a list of similar successful titles, please generate metadata for a new blog post.

        **Blog Content (first 2000 characters):**
        ---
        {content[:2000]}
        ---

        **Similar Successful Titles for Inspiration:**
        ---
        {chr(10).join(f"- {title}" for title in title_examples)}
        ---

        **Your Task:**
        Generate the following items. Do not add any extra commentary.

        1. **Three catchy blog titles:**
           - Each title must be under 70 characters.

        2. **SEO meta description:**
           - This must be exactly 155 characters long.

        3. **Five relevant keywords:**
           - Provide a comma-separated list.
        """
        print("🤖 Calling Google GenAI to generate suggestions...")
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return self.parse_llm_response(response.content)

    def generate_with_simple_heuristics(self, content: str, similar_titles: List[Tuple[str, float, str]]) -> BlogSuggestion:
        """Generate suggestions using simple heuristics (fallback when no LLM)"""
        headings = [line.strip('#').strip() for line in content.split('\n') if line.strip().startswith('#')]
        base_titles = [title for title, _, _ in similar_titles[:3] if len(title) < 60]
        if headings:
            main_topic = headings[0][:50]
            base_titles.append(f"A Complete Guide to {main_topic}")
        while len(base_titles) < 3: base_titles.append("Exploring Key Concepts In This Topic")
        
        first_paragraph = next((line.strip()[:155] for line in content.split('\n') if line.strip() and not line.strip().startswith('#')), f"Learn about {headings[0] if headings else 'this exciting topic'} with our comprehensive guide.")
        
        return BlogSuggestion(
            titles=base_titles[:3],
            meta_description=first_paragraph,
            slug=self.create_slug(base_titles[0]),
            keywords=self.extract_keywords(content),
            confidence=0.6
        )

    def generate_suggestions(self, markdown_content: str) -> BlogSuggestion:
        """Main function to generate blog suggestions"""
        print("\n🎯 Generating suggestions...")
        similar_titles = self.find_similar_titles(markdown_content, top_k=15)
        print("\n🔍 Top similar titles found (for context):")
        for i, (title, score, category) in enumerate(similar_titles[:5]):
            print(f"  {i+1}. {title} (similarity: {score:.3f}, category: {category})")

        if self.llm:
            suggestions = self.generate_with_llm(markdown_content, similar_titles)
        else:
            print("\n⚠️ LLM not available. Using simple heuristics as a fallback.")
            suggestions = self.generate_with_simple_heuristics(markdown_content, similar_titles)
        
        print("\n✨ Generated suggestions:")
        print(f"  📝 Titles: {suggestions.titles}")
        print(f"  📄 Meta Description: {suggestions.meta_description}")
        print(f"  🔗 Slug: {suggestions.slug}")
        print(f"  🏷️ Keywords: {suggestions.keywords}")
        print(f"  📈 Confidence: {suggestions.confidence}")
        
        return suggestions

def load_markdown_file(file_path: str) -> str:
    """Load markdown content from file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    """Main function to run the blog suggestion system"""
    print("🌟 Blog Title & Metadata Suggestion System")
    print("=" * 50)
    
    DATASET_PATH = r"D:\me\blog_post\medium_post_titles.csv"  # IMPORTANT: Update this path
    README_PATH = r"D:\me\blog_post\team_icebreakers_blog.md"
    
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Dataset file not found: {DATASET_PATH}")
        return
        
    if not os.path.exists(README_PATH):
        print(f"📝 Creating sample blog file: {README_PATH}")
        sample_content = """# Machine Learning in Production
        Machine learning has transformed from a research field to a critical business capability. However, deploying ML models in production environments presents unique challenges that go beyond model accuracy.
        ## The Challenge of Production ML
        Most data scientists focus on model performance metrics like accuracy, precision, and recall. While these metrics are important, production ML systems require additional considerations like scalability, reliability, monitoring, and handling data drift.
        ## Best Practices for ML Deployment
        To succeed, always version your models using tools like MLflow. Use A/B testing to deploy new models gradually and implement comprehensive monitoring for performance, data quality, and system health.
        """
        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(sample_content)
    
    try:
        engine = BlogSuggestionEngine(DATASET_PATH)
        print(f"\n📖 Loading blog content from: {README_PATH}")
        blog_content = load_markdown_file(README_PATH)
        
        suggestions = engine.generate_suggestions(blog_content)
        
        results = {
            "titles": suggestions.titles,
            "meta_description": suggestions.meta_description,
            "slug": suggestions.slug,
            "keywords": suggestions.keywords,
            "confidence": suggestions.confidence
        }
        
        with open("blog_suggestions.json", "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: blog_suggestions.json")
        print("\n🎉 Blog suggestion generation completed!")
        
    except Exception as e:
        print(f"❌ An unexpected error occurred: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()