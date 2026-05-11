
import os
import shutil
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

VECTOR_STORE_DIR = "vector_stores"
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

def process_document(file_path: str, filename: str, username: str):
    if filename.lower().endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif filename.lower().endswith(".txt"):
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise Exception("Unsupported file type")

    documents = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    docs = splitter.split_documents(documents)

    user_index_path = os.path.join(VECTOR_STORE_DIR, username, "active_index")
    
    if os.path.exists(user_index_path):
        shutil.rmtree(user_index_path)
    os.makedirs(user_index_path, exist_ok=True)

    vector_store = FAISS.from_documents(docs, embeddings)
    vector_store.save_local(user_index_path)
    return True

def query_active_document(query: str, username: str):
    user_index_path = os.path.join(VECTOR_STORE_DIR, username, "active_index")
    
    if not os.path.exists(user_index_path):
        return "No active document found. Please uploasd one first.", []

    vs = FAISS.load_local(user_index_path, embeddings, allow_dangerous_deserialization=True)
    relevant_chunks = vs.similarity_search(query, k=4)

    if not relevant_chunks:
        return "I'm sorry, I couldn't find an answer in your documents.",[]

    context_text = "\n".join([c.page_content for c in relevant_chunks])
    
    prompt = ChatPromptTemplate.from_template("""
    Answer ONLY using the context provided. If not in context, say you don't know.
    Context: {context}
    Question: {question}
    Answer:""")
    
    chain = prompt | llm
    try:
        response = chain.invoke({"context": context_text, "question": query})
        return response.content, relevant_chunks
    except Exception as e:
        return f"Error connecting to LLM: {str(e)}", []

def delete_active_document(username: str):
    user_index_path = os.path.join(VECTOR_STORE_DIR, username, "active_index")
    if os.path.exists(user_index_path):
        shutil.rmtree(user_index_path)
        return True
    return False