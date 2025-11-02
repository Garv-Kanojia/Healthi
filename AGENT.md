now i want you to create a plan for chat-interface as a django app. below are my requirements:

1. The user can only have maximum 3 chats.
2. The user can delete and create new chats. Every chat can have different names, that can be changed anytime by user. By default every chat name is Chat. the chat_id will be unique, which will be created_at field, which will be used for vector search. The username will be complete email address for vector search.
3. The prompt-response pair will be stored in encrypted prompt as json object in pgSQL. And will be chunked and stored as vectors with metadata in chromaDB as done RAG_LLM.py file.
4. the user is allowed to input atmost 5 images and 2 PDFs (max 5 pages per pdf). The name of the file will only be stored in the pgSQL, and the data will be attached to the current prompt and then stored as vector with proper metadata in chromaDB.
5. There will be a toggle button for recording speech, which will be transcribed and showed in real-time on the input area.
6. When a user login, only the names of the chat will be fetched from the DB and shown on the screen. When the user clicks on a chat, all the prompt-response pairs along with the files used (images and pdf names) will be fetch for the chat.
7. When a chat is deleted the json objects and all other info about it is also deleted from pgSQL and the vectors under the username (email) and the specific chat_id (created_at) will also be deleted.
8. When a person uploads a file (image/pdf), the format will be checked, the size (for image 10mb and for pdf 25mb) will be checked, and other constrainst like pages will be checked. Then it will be given to a separated microservice through API, and a extracted and cleaned text will be returned in json format have key as "text".

Create a plan for the chat interface, the plan must be in such a way that a coding agent can easily create the perfect replica of my idea with no issues. Leave the testing part for now. No need of frontend for now. Use the already existing conda environment auth_env for any dependency.
Also use the logic in the PAG_LLM file and speech_to_text files for creating those services. As either they give output to a frontend or to CLI those code are not furnished.
Store the plan in Plans folder.
