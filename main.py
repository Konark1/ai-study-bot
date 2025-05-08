import json
import os
import fitz  # PyMuPDF
from gpt4all import GPT4All
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class StudyBot:
    def __init__(self):
        try:
            self.model = GPT4All("mistral-7b-instruct-v0.1.Q4_0.gguf", model_path="models/")
        except Exception as e:
            logging.error(f"Failed to load GPT4All model: {str(e)}")
            exit(1)
        self.formulas_file = "formulas.json"
        self.formulas_db = {}
        self.init_formulas_db()

    def validate_and_fix_json(self):
        try:
            # Attempt to load the JSON file
            with open(self.formulas_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if the "formulas" key exists and is a dictionary
            if not isinstance(data.get("formulas", {}), dict):
                raise ValueError("Invalid structure: 'formulas' key is not a dictionary.")
            
            logging.info("JSON file is valid.")
            return data  # Return the valid data

        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
            logging.error(f"Invalid JSON file: {str(e)}. Resetting to default.")
            
            # Reset the JSON file to a valid default state
            default_data = {"formulas": {}}
            with open(self.formulas_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            
            return default_data  # Return the default data

    def init_formulas_db(self):
        # Validate and fix the JSON file if necessary
        data = self.validate_and_fix_json()
        self.formulas_db = data.get("formulas", {})

    def get_formula(self, query):
        query_lower = query.lower()
        
        # Check if the formula exists in memory
        if query_lower in self.formulas_db:
            logging.info(f"Formula for '{query_lower}' found in database.")
            return f"📘 From Database:\n{self.formulas_db[query_lower]}"
        
        # Generate a new formula if not found
        logging.info(f"Formula for '{query_lower}' not found. Generating...")
        response = self.model.generate(f"Provide the exact formula for {query} with brief explanation. Use LaTeX math formatting with $$ when appropriate.")
        
        # Update the in-memory database and save to file
        self.formulas_db[query_lower] = response
        try:
            with open(self.formulas_file, 'w', encoding='utf-8') as f:
                json.dump({"formulas": self.formulas_db}, f, indent=2)
            logging.info(f"Formula for '{query_lower}' saved to formulas.json.")
        except Exception as e:
            logging.error(f"Failed to save formula to file: {str(e)}")
        
        return f"🧠 New Formula:\n{response}"

    def query_pdf(self, filename, question):
        try:
            text = ""
            filepath = os.path.join("documents", filename)
            
            # Check if the file exists
            if not os.path.exists(filepath):
                logging.error(f"File '{filename}' not found.")
                return f"❌ Error: File '{filename}' not found."

            # Open and extract text from the PDF
            with fitz.open(filepath) as doc:
                for i, page in enumerate(doc):
                    if i >= 10:  # Limit to the first 10 pages
                        break
                    text += page.get_text()
            
            # Check if the document is empty
            if not text.strip():
                logging.warning("The document is empty or unreadable.")
                return "❌ Error: The document is empty or unreadable."

            # Generate a response using the extracted text
            logging.info("Generating response from the model...")
            response = self.model.generate(
                f"Answer based on this document:\n{text[:10000]}\n\nQuestion: {question}\nAnswer:"
            )
            logging.info("Response generated successfully.")
            return f"📄 PDF Answer:\n{response}"
        except Exception as e:
            logging.error(f"Error while processing PDF query: {str(e)}")
            return f"❌ Error: {str(e)}"

    def list_files(self):
        # List all PDF files in the documents directory
        try:
            files = [f for f in os.listdir("documents") if f.endswith('.pdf')]
            logging.info(f"Found {len(files)} PDF(s) in the documents directory.")
            return files
        except Exception as e:
            logging.error(f"Error listing files in 'documents' directory: {str(e)}")
            return []

def main():
    bot = StudyBot()
    print("🔍 AI Study Bot - Type 'help' for commands")
    
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            print("❌ Please enter a command. Type 'help' for available commands.")
            continue

        logging.info(f"User input received: '{user_input}'")
        
        if user_input.lower() in ['exit', 'quit']:
            logging.info("Exiting the bot.")
            break
            
        elif user_input.lower() == 'help':
            print("\nCommands:")
            print("ask <question> - Get a formula")
            print("pdf <filename> <question> - Query a PDF")
            print("list - Show available PDFs")
            print("exit - Quit")
            
        elif user_input.lower() == 'list':
            files = bot.list_files()
            print("\nAvailable PDFs:" if files else "\nNo PDFs found")
            for f in files:
                print(f"- {f}")
                
        elif user_input.lower().startswith('pdf '):
            parts = user_input.split(maxsplit=2)
            if len(parts) < 3:
                print("Usage: pdf filename.pdf 'your question'")
            else:
                print(bot.query_pdf(parts[1], parts[2]))
                
        elif user_input.lower().startswith('ask '):
            print(bot.get_formula(user_input[4:]))
            
        else:
            print("❌ Invalid command. Type 'help' for available commands.")

if __name__ == "__main__":
    main()