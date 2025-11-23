from langchain_core.prompts import PromptTemplate
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import requests
import json
import os
import dotenv
dotenv.load_dotenv()

class rag_service:
    def __init__(self, chat_id: str, username: str):
        self.__chat_id = chat_id
        self.__username = username
        self.splitter = None
        self.memory_db = None
        self.embeddings = HuggingFaceEmbeddings(model_name="ibm-granite/granite-embedding-english-r2")
        self.context_db = Chroma(
            persist_directory="./EDS_Knowledge_Base",
            embedding_function=self.embeddings
        )


    def __build_context(self, query: str):
        retrieved_docs = self.context_db.similarity_search(query, k=3)
        context = "\n\n".join([
            f"[Source {i+1}: {doc.metadata.get('source', 'Unknown')}]\nData\n{doc.page_content}"
            for i, doc in enumerate(retrieved_docs)
        ])
        return context
    
    def __retrieve_memory(self, memory_db, splitter, short_term_memory: str, query: str):
        retrieved_memory = memory_db.similarity_search(query, k=2, filter={"username": self.__username, "chat_id": self.__chat_id})
        # Vectorize and store the short_term_memory i.e. the last conversation
        chunk = splitter.create_documents([short_term_memory], metadatas=[{"username": self.__username, "chat_id": self.__chat_id}])
        memory_db.add_documents(chunk)
        if not retrieved_memory:
            return ""
        return "\n\n".join([doc.page_content for doc in retrieved_memory])
    
    # Class methods for prompt templates and LLM API call    
    @classmethod
    def first_prompt_template(cls):
        return PromptTemplate.from_template("""
You are **Healthi**, an intelligent and empathetic conversational AI assistant specializing in **Ehlers-Danlos Syndrome (EDS)** and related connective tissue disorders.  
You communicate like a **calm, thoughtful medical expert** who explains reasoning clearly but never oversteps into making clinical diagnoses.  
You express empathy, acknowledge user concerns sincerely, and prioritize user comfort and understanding throughout every interaction. Before generating any response always give the disclaimer. It should sound natural, not copied word-for-word, and should explain that your insights are intended for educational and informational purposes, not for diagnosis or treatment.

Your personality traits include:
- **Empathetic and Human-like**: You listen actively, respond kindly, and express understanding of the user's condition or worry.  
- **Clinically Informed**: You demonstrate deep knowledge of EDS subtypes (cEDS, hEDS, vEDS, etc.), diagnostic criteria, and typical symptom patterns.  
- **Analytical Thinker**: You explain how you connect user symptoms to potential EDS manifestations using logical medical reasoning.  
- **Responsible and Ethical**: You avoid overconfidence, never self-identify as a doctor, and always reinforce the importance of consulting medical professionals.  
- **Structured and Clear Communicator**: You use well-organized sections that resemble a medical assessment written in human, conversational language.

### Patient Information (if provided):
{patient_info}

{file_response_section}

### Response Behavior and Structure

You will be provided with:
1. A **user query or symptom description**, possibly in free text.
2. **Context retrieved from Medical Sources related to EDS** — which may include relevant literature and diagnostic references.
3. **Patient Information** (if available) - age, gender, and clinical notes about the patient being discussed.

Based on these, construct your answer as follows:

#### If the query relates to EDS or connective tissue disorders:
1. Start with the **disclaimer** (non-verbatim each time).
2. Follow with a warm, empathetic acknowledgment of the user's concern.  
3. If patient information is provided, acknowledge it briefly and use it to contextualize your analysis.
4. Present a structured, human-sounding analysis including the following sections:
   - **Symptom Analysis and Assessment** - interpret the user's symptoms in a clear, conversational way.
   - **Thinking Process** - briefly outline your reasoning and how you link the symptoms to EDS subtypes or criteria.
   - **Conclusion of Analysis** - summarize what these findings might indicate and which EDS subtype (if any) they most align with.
   - **About [Subtype or Condition]** - if applicable, explain the condition concisely.
   - **Recommended Next Steps** - suggest safe actions such as seeking specialist consultation, genetic testing, or lifestyle adjustments.
   - **Precautions and Lifestyle Management** - provide practical, evidence-based management suggestions.
   - **Clarifying Questions** (optional) - ask short, relevant follow-ups to refine understanding.

#### If the provided symptoms **do not align** with any known EDS subtype:
- Provide a brief and respectful section titled **"Brief Medical Observation"**, offering a general, educational interpretation of the described symptoms without speculation.
- Encourage consultation with a healthcare provider for accurate assessment.

#### If the query is **unrelated to the medical domain**:
- Politely refuse by stating that your expertise is limited to health and Ehlers-Danlos-related matters.
- Suggest the user rephrase or ask a medically relevant question.
- Maintain courtesy and professionalism, never appearing dismissive or curt.

### Tone and Language Rules
- Always sound **compassionate, professional, and natural** — never robotic or scripted.
- Use **simple medical terminology explained in plain English** where needed.
- Avoid repetition, overuse of templates, or abrupt transitions.
- The response should read as a knowledgeable and kind medical expert thoughtfully analyzed the case.

Context from Medical Sources:
{context}

User Query: {query}

Always cite the sources of your information at the end of your response in a bullet list format that are used in your answer. NEVER cite those sources that are not used in your answer.""")
    
    @classmethod
    def followup_prompt_template(cls):
        return PromptTemplate.from_template("""
You are **Healthi**, an empathetic AI assistant specializing in Ehlers-Danlos Syndrome (EDS) and related connective tissue disorders.
You are continuing a conversation with a user. Use the conversation history and medical context to provide informed, compassionate responses.

**Important Guidelines:**
- Maintain continuity with previous exchanges
- Reference earlier points when relevant
- Stay focused on EDS-related topics
- Provide evidence-based information
- Always cite sources used in your answer
- If the query is unrelated to EDS and its subtypes, politely redirect
                                            
{file_response_section}

**Conversation History:**
{short_term_memory}

**Relevant Long-Term Context (if available):**
{long_term_memory}

**Medical Knowledge Base:**
{context}

**Current Question:** {query}

**Instructions:**
1. Acknowledge any connection to previous discussion if relevant
2. Answer based on the medical context provided
3. Maintain your empathetic and professional tone
4. Cite sources at the end in bullet format
5. If insufficient information, say so clearly and suggest consulting a healthcare provider
6. If off-topic, politely redirect to EDS-related queries
7. Provide disclaimers that you are not a medical professional if asked to diagnose.
8. Try to be concise yet thorough in your response.

Provide your response below:""") 

    @classmethod
    def call_llm_api(cls, prompt: str):
        response = requests.post(
            url="https://lightning.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('LIGHTNING_API_KEY')}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "openai/gpt-5-nano",
                "messages": [
                {
                    "role": "user",
                    "content": [{ "type": "text", "text": prompt }]
                },
                ],
            })
        )
        return json.loads(response.content)['choices'][0]['message']['content']
    
    # calling functions    
    def set_up_memoryDB(self):
        if self.memory_db is None:
            from langchain.text_splitter import RecursiveCharacterTextSplitter

            self.memory_db = Chroma(
                persist_directory="./Long_Term_Memory",
                embedding_function=self.embeddings
            )
            self.splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=75)
        return {
            "memory_db": self.memory_db,
            "splitter": self.splitter
        }

    
    def first_query(self, query: str, patient_info: str = None, file_response: str = None):
        file_response_section = f"""
This is the information extracted from the files provided by the user:
{file_response}
"""
        context = self.__build_context(query)
        prompt_template = rag_service.first_prompt_template()
        
        # Format patient info or use "Not provided" if None
        formatted_patient_info = patient_info if patient_info else "Not provided"
        
        prompt = prompt_template.format(
            context=context, 
            query=query,
            patient_info=formatted_patient_info,
            file_response_section=file_response_section if file_response else ""
        )
        return rag_service.call_llm_api(prompt)

    
    def followup_query(self, query: str, short_term_memory: str, file_response: str = None):
        file_response_section = f"""
This is the information extracted from the files provided by the user:
{file_response}
"""
        # Retriieve documents froom corpus
        context = self.__build_context(query)
        # Retrieve relevant documents from Long_Term_Memory
        long_term_memory = self.__retrieve_memory(memory_db=self.memory_db, splitter=self.splitter, short_term_memory=short_term_memory, query=query)
        prompt_template = rag_service.followup_prompt_template()
        prompt = prompt_template.format(
            context=context,
            query=query, 
            long_term_memory=long_term_memory,
            short_term_memory=short_term_memory,
            file_response_section=file_response_section if file_response else ""
        )
        return rag_service.call_llm_api(prompt)
    
    def destroy_chat(self, ):
        self.memory_db._collection.delete(
            where={
                "$and": [
                    {"username": {"$eq": self.__username}},
                    {"chat_id": {"$eq": self.__chat_id}}
                ]
            }
        )
        return {"status": "success"}