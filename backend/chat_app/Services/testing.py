import chromadb

db = chromadb.PersistentClient(path="/chat_app/Services/EDS_Knowledge_Base")

collection = db.get_or_create_collection(name="langchain")
print("Size = ", collection.count())