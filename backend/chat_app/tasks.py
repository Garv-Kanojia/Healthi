from celery import shared_task
from .Services.rag import rag_service

@shared_task
def delete_chat_remains(chat_id, username):
    """
    Background task to delete chat vectors and associated heavy data.
    """
    try:
        rag = rag_service(chat_id=chat_id, username=username)
        rag.set_up_memoryDB()
        result = rag.destroy_chat()
        print(f"Chat {chat_id} memory destroyed: {result}")
        return f"Chat {chat_id} cleanup successful"
    except Exception as e:
        print(f"Error in delete_chat_remains for {chat_id}: {e}")
        return f"Error: {str(e)}"