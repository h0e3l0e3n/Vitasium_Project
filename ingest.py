import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

load_dotenv()
PROGRESS_FILE = "ingest_progress.txt"
INDEX_NAME = "vitasium-index"
BATCH_SIZE = 90  

print("Vitasium is reading the Encyclopedia")
loader = PyPDFLoader("data/Gale_Encyclopedia.pdf")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
docs = loader.load_and_split(text_splitter=text_splitter)

start_index = 0
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r") as f:
        try:
            line = f.read().strip()
            if line:
                start_index = int(line)
                print(f"Resuming from snippet {start_index}")
        except ValueError:
            start_index = 0

# PINECONE
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

if INDEX_NAME not in pc.list_indexes().names():
    print("Creating new 3072-dim Memory Space")
    pc.create_index(
        name=INDEX_NAME,
        dimension=3072, 
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
    while not pc.describe_index(INDEX_NAME).status['ready']:
        time.sleep(100)

raw_keys = [
    os.getenv("GOOGLE_API_KEY_1"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4")
]

keys = [k.strip() for k in raw_keys if k and len(k.strip()) > 10]
current_key_idx = 0

i = start_index
while i < len(docs):
    success = False
    
    try:
        active_key = keys[current_key_idx]
        os.environ["GOOGLE_API_KEY"] = active_key
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001", 
            google_api_key=active_key,
            task_type="retrieval_document"
        )
        
        vector_store = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
        
        batch = docs[i : i + BATCH_SIZE]
        vector_store.add_documents(batch)

        current_pos = i + len(batch)
        with open(PROGRESS_FILE, "w") as f:
            f.write(str(current_pos))
            
        print(f"Key {current_key_idx + 1}: Uploaded {current_pos} / {len(docs)} snippets")
        
        time.sleep(20) 
        i += BATCH_SIZE 
        
    except Exception as e:
        error_msg = str(e)
        
        if "429" in error_msg:
            if "Quota exceeded for metric" in error_msg and "limit: 1000" in error_msg:
                print(f"Key {current_key_idx + 1} hit DAILY limit. Moving to next key")
                current_key_idx += 1
            else:
                print(f"Key {current_key_idx + 1} hit minute limit. Resting")
                time.sleep(100)
        
        elif "400" in error_msg or "INVALID_ARGUMENT" in error_msg:
            print(f"Key {current_key_idx + 1} rejected. Skipping")
            current_key_idx += 1
        else:
            print(f"Unexpected Error: {e}")
            break

    if current_key_idx >= len(keys):
        print("\nAll keys cycled. Checking if any have reset")
        time.sleep(300)
        current_key_idx = 0 

print("Vitasium's brain is fully loaded.")