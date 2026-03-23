from celery import shared_task
from pinecone import Pinecone
import os
from dotenv import load_dotenv
load_dotenv()

@shared_task
def delete_chat_remains(chat_id, username):
    """
    Background task to delete chat vectors and associated heavy data.
    """
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index(host=os.getenv("PINECONE_HOST"))
        index.delete(
            filter={
                "$and": [
                    {"email": {"$eq": username}},
                    {"chatID": {"$eq": chat_id}}
                ]
            },
            namespace="memory-vectorindex" 
        )
        print(f"Chat {chat_id} memory destroyed")
        return f"Chat {chat_id} cleanup successful"
    except Exception as e:
        print(f"Error in delete_chat_remains for {chat_id}: {e}")
        return f"Error: {str(e)}"