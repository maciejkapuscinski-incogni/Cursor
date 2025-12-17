import os
import json
from dotenv import load_dotenv
from serpapi import GoogleSearch
from openai import OpenAI
import requests

# Load environment variables from .env file
load_dotenv()

# Get environment variables
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def search_google(name, company):
    """
    Search Google using SerpAPI for the given name and company.
    
    Args:
        name (str): The person's name to search for
        company (str): The company/workplace name
    
    Returns:
        list: A list of dictionaries containing 'title', 'snippet', and 'link' 
              for up to 10 results. Returns empty list on error.
    """
    try:
        # Check if API key is available
        if not SERPAPI_KEY:
            print("Error: SERPAPI_KEY not found in environment variables.")
            return []
        
        # Create search query combining name and company
        query = f"{name} {company}"
        
        # Perform the search
        search = GoogleSearch({
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 10  # Get top 10 results
        })
        
        results = search.get_dict()
        
        # Extract organic results
        search_results = []
        if "organic_results" in results:
            for result in results["organic_results"][:10]:  # Limit to 10
                search_results.append({
                    "title": result.get("title", "No title"),
                    "snippet": result.get("snippet", "No snippet available"),
                    "link": result.get("link", "No link available")
                })
        
        return search_results
        
    except Exception as e:
        print(f"Error occurred while searching Google: {str(e)}")
        return []


def summarize_results(name, results):
    """
    Format search results and send them to OpenAI to generate a funny summary.
    
    Args:
        name (str): The person's name
        results (list): List of search result dictionaries with 'title', 'snippet', and 'link'
    
    Returns:
        str: AI-generated summary, or error message if something goes wrong
    """
    try:
        # Check if API key is available
        if not OPENAI_API_KEY:
            return "Error: OPENAI_API_KEY not found in environment variables."
        
        # Format the search results nicely
        formatted_results = ""
        for i, result in enumerate(results, 1):
            formatted_results += f"Result {i}:\n"
            formatted_results += f"Title: {result.get('title', 'N/A')}\n"
            formatted_results += f"Snippet: {result.get('snippet', 'N/A')}\n"
            formatted_results += f"Link: {result.get('link', 'N/A')}\n\n"
        
        # Create the prompt
        prompt = f"""Based on these Google search results about {name}, write a funny 2-3 sentence introduction about this person. Include interesting details. We are a data removal company so we don't want our data out there. If you find an email or phone number, make a joke about it. But definitely skip whe wordking of current company that he/she is working at. Focus only on skills and experience. And skip position.

Search Results:
{formatted_results}"""
        
        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Send to OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a humorous writer who creates funny introductions about people based on their online presence."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.8
        )
        
        # Extract and return the summary
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        return f"Error occurred while generating summary: {str(e)}"


def send_to_slack(message):
    """
    Send a message to Slack using the configured webhook URL.

    Args:
        message (str): The text message to send.
    """
    if not SLACK_WEBHOOK_URL:
        print("Warning: SLACK_WEBHOOK_URL not configured; skipping Slack notification.")
        return

    try:
        payload = {"text": message}
        response = requests.post(
            SLACK_WEBHOOK_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10,
        )
        response.raise_for_status()
        print("Slack notification sent successfully.")
    except Exception as ex:
        print(f"Failed to send Slack notification: {ex}")


def main():
    """Main function to run the application."""
    # Ask user for their name
    name = input("Please enter your name: ")
    
    # Ask user for their workplace/company
    workplace = input("Please enter your workplace/company: ")
    
    # Print greeting with name and workplace
    print(f"\nHello {name}! Welcome to {workplace}.")
    
    # Search Google for the user's name and company
    print(f"\nSearching Google for '{name} {workplace}'...")
    results = search_google(name, workplace)
    
    # Print the search results
    if results:
        print(f"\nFound {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   {result['snippet']}")
            print(f"   {result['link']}\n")
        
        # Generate and print AI summary
        print("Generating AI summary...")
        summary = summarize_results(name, results)
        print(f"\n{'='*60}")
        print("AI-Generated Summary:")
        print(f"{'='*60}")
        print(summary)
        print(f"{'='*60}\n")

        # Send summary to Slack
        send_to_slack(summary)
    else:
        print("\nNo results found or an error occurred.")


if __name__ == "__main__":
    main()
