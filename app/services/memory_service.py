import os
from simplemem import SimpleMemConfig, set_config, SimpleMemSystem

def init_simplemem():
    """
    Initializes global settings for the application.
    This should be called once (e.g., in your main.py or app startup).
    """
    config = SimpleMemConfig(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        llm_model="gpt-4.1-mini",
        embedding_model="Qwen/Qwen3-Embedding-0.6B",
        enable_parallel_processing=True,
        max_parallel_workers=8,
    )
    # Applying the config globally as per official 'Using SimpleMemConfig' guide
    set_config(config)

class MemoryService:
    def __init__(self, contact_id: str):
        self.contact_id = contact_id
        
        # 1. Dynamic Path Construction for Docker Persistence
        base_storage = os.getenv("SIMPLEMEM_STORAGE_PATH", "/app/memory_db")
        self.db_path = os.path.join(base_storage, f"contact_{contact_id}")
        
        # Ensure the directory exists inside the container
        os.makedirs(self.db_path, exist_ok=True)
        
        # 2. Correct Initialization
        # SimpleMemSystem takes db_path for the vector store location.
        # It inherits API keys and models from the global config set earlier.
        self.system = SimpleMemSystem(
            db_path=self.db_path,
            clear_db=False
        )

    def add_message(self, role: str, content: str, conversation_id: str, timestamp: str):
        """Adds a message to the buffer with specific session context."""
        self.system.add_dialogue(
            speaker=role, 
            content=f"[Session: {conversation_id}] {content}", 
            timestamp=timestamp
        )

    def finalize(self):
        """Processes the buffer and persists facts to the contact-specific db_path."""
        self.system.finalize()

    def ask_memory(self, question: str) -> str:
        """Performs hybrid retrieval to answer based on historical facts."""
        return self.system.ask(question)