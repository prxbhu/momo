import os
import psycopg2
import json
import httpx

POSTGRES_URL = os.getenv("POSTGRES_URL")
# Use Ollama for memory embeddings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

def get_db_connection():
    return psycopg2.connect(POSTGRES_URL)

async def get_embedding(text: str) -> list[float]:
     """Get embedding from Ollama API using nomic-embed-text."""
     url = f"{OLLAMA_URL.rstrip('/')}/api/embeddings"
     data = {
          "model": "nomic-embed-text",
          "prompt": text
     }
     
     async with httpx.AsyncClient() as client:
          res = await client.post(url, json=data, timeout=30.0)
          res.raise_for_status()
          return res.json()["embedding"]

async def remember_fact(fact: str, category: str = "general") -> str:
    """Store a fact or piece of information in MOMO's long-term memory.
    Args:
        fact: The information to remember
        category: Category tag (e.g. 'personal', 'preferences', 'general')
    Returns:
        Confirmation that the fact was stored
    """
    if not POSTGRES_URL:
        return "Database URL is not configured."
        
    try:
         embedding = await get_embedding(fact)
         
         conn = get_db_connection()
         with conn.cursor() as cur:
              cur.execute(
                   "INSERT INTO memories (content, embedding, source) VALUES (%s, %s, %s)",
                   (fact, json.dumps(embedding), f"manual_{category}")
              )
         conn.commit()
         conn.close()
         return f"Successfully remembered: {fact}"
         
    except Exception as e:
         return f"Error remembering fact: {e}"

async def recall_facts(query: str, top_k: int = 3) -> str:
    """Recall facts from MOMO's long-term memory relevant to a query.
    Args:
        query: The topic or question to search memory for
        top_k: Number of relevant memories to return
    Returns:
        Relevant stored facts as a formatted string
    """
    if not POSTGRES_URL:
        return "Database URL is not configured."
        
    try:
         embedding = await get_embedding(query)
         
         conn = get_db_connection()
         with conn.cursor() as cur:
              # pgvector cosine distance operator: <=>
              cur.execute(
                   """
                   SELECT content 
                   FROM memories 
                   ORDER BY embedding <=> %s::vector 
                   LIMIT %s
                   """,
                   (json.dumps(embedding), top_k)
              )
              results = cur.fetchall()
         conn.close()
         
         if not results:
              return "No relevant memories found."
              
         facts = [row[0] for row in results]
         return "Recalled facts:\n" + "\n".join(f"- {f}" for f in facts)
         
    except Exception as e:
          return f"Error recalling facts: {e}"
