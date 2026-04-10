import os
import httpx
from bs4 import BeautifulSoup
import json

async def search_web(query: str) -> str:
    """Search the web for a query and return a summary of results.
    Use for: current events, recent news, live prices, anything that may have changed recently.
    Args:
        query: The search query string
    Returns:
        A formatted string of search results
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "Error: SERPER_API_KEY is not set."
    
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query
    })
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if "answerBox" in data:
                ans = data["answerBox"]
                if "snippet" in ans:
                    results.append(f"Answer: {ans['snippet']}")
                elif "answer" in ans:
                     results.append(f"Answer: {ans['answer']}")
            
            if "organic" in data:
                for item in data["organic"][:5]: # Top 5 results
                    results.append(f"- {item.get('title')}: {item.get('snippet')} ({item.get('link')})")
            
            if not results:
                return "No useful results found."
            
            return "\n".join(results)
    except Exception as e:
        return f"Error performing web search: {e}"

async def fetch_url(url: str) -> str:
    """Fetch and extract the main text content from a URL.
    Use when user provides a URL.
    Args:
        url: The full URL to fetch
    Returns:
        Extracted text content from the page
    """
    try:
        async with httpx.AsyncClient() as client:
             response = await client.get(url, timeout=15.0)
             response.raise_for_status()
             
             soup = BeautifulSoup(response.text, 'html.parser')
             
             # Remove script and style elements
             for script in soup(["script", "style"]):
                 script.extract()
                 
             # Get text
             text = soup.get_text()
             
             # Break into lines and remove leading and trailing space on each
             lines = (line.strip() for line in text.splitlines())
             # Break multi-headlines into a line each
             chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
             # Drop blank lines
             text = '\n'.join(chunk for chunk in chunks if chunk)
             
             # Limit to 5000 characters to avoid context overflow
             return text[:5000] + ("..." if len(text) > 5000 else "")
             
    except Exception as e:
        return f"Error fetching URL: {e}"

async def get_news(topic: str = "technology") -> str:
    """Get the latest news headlines for a topic.
    Args:
        topic: News topic (e.g. technology, sports, world)
    Returns:
        A formatted list of news headlines with summaries
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "Error: SERPER_API_KEY is not set."
        
    url = "https://google.serper.dev/news"
    payload = json.dumps({
        "q": topic
    })
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
         async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if "news" in data:
                for item in data["news"][:5]:
                    results.append(f"- {item.get('title')}: {item.get('snippet')} ({item.get('source')})")
                    
            if not results:
                return "No news found."
                
            return "\n".join(results)
    except Exception as e:
         return f"Error fetching news: {e}"
