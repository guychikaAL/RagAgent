# Auto Claims Q&A GUI App 🚗

A simple web-based interface to ask questions about `auto_claim_20_forms_FINAL.pdf`.

## 🚀 Quick Start

### 1. Install Requirements

```bash
# If not already installed
pip install streamlit

# Or install from requirements
cd app
pip install -r requirements.txt
```

### 2. Make Sure RAG System is Ready

```bash
# Ensure you have:
# ✅ Production index created
# ✅ OpenAI API key in .env file
# ✅ All main dependencies installed
```

### 3. Run the App

```bash
# From the app directory
streamlit run gui_app.py

# Or from project root
streamlit run app/gui_app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📋 Features

### 🎯 Simple Interface
- Clean, user-friendly design
- Text input for questions
- Clear answer display

### 🤖 Powered by RAG
- Routes questions to appropriate agents
- Retrieves relevant information
- Provides grounded, accurate answers

### 📊 Transparency
- Shows routing decision
- Displays confidence scores
- Lists sources
- Shows retrieved chunks

### 💡 Example Questions
Built-in examples in sidebar:
- "What is Jon Mor's phone number?"
- "Summarize Jon Mor's entire claim"
- "When did David Ross's accident occur?"

---

## 🎨 What You'll See

### Main Screen
```
🚗 Auto Claims Q&A System
Hello! Ask me anything about auto_claim_20_forms_FINAL.pdf

[Text input box]
[Get Answer button]

💡 Answer
[Answer appears here]

📊 Metadata
Route: NEEDLE | Confidence: 0.95 | Sources: 1
```

### Sidebar
- System information
- Example questions
- Configuration details

---

## 🔧 How It Works

```
User Question
     ↓
[Router Agent] → Classifies question type
     ↓
[Needle/Summary Agent] → Retrieves & answers
     ↓
[GUI Display] → Shows answer + metadata
```

---

## 📁 Files

```
app/
├── gui_app.py          ← Main Streamlit app
├── requirements.txt    ← GUI dependencies
└── README.md           ← This file
```

---

## ⚙️ Configuration

### Change RAG Settings

Edit `gui_app.py` lines 39-45:

```python
needle_retriever = index_manager.get_needle_retriever(
    top_k=3,              # Number of chunks
    similarity_threshold=0.75,  # Similarity filter
)
```

### Change Models

Edit lines 48-50:

```python
router_agent = RouterAgent(model="gpt-4o-mini", temperature=0.0)
needle_agent = NeedleAgent(model="gpt-4o-mini", temperature=0.0)
summary_agent = SummaryAgent(model="gpt-4o-mini", temperature=0.2)
```

---

## 🐛 Troubleshooting

### Issue: "Failed to initialize RAG system"

**Solutions**:
1. Check that `production_index` exists:
   ```bash
   ls -la production_index/
   ```

2. Verify OpenAI API key:
   ```bash
   cat .env | grep OPENAI_API_KEY
   ```

3. Install all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Issue: "Module not found"

**Solution**: Run from project root:
```bash
cd /path/to/RagAgentv2
streamlit run app/gui_app.py
```

### Issue: App is slow

**Solution**: This is normal on first load. The RAG system is cached after initialization.

---

## 🎯 Example Usage

### Question: "What is Jon Mor's phone number?"

**Answer**:
```
(555) 100-2000
```

**Metadata**:
- Route: NEEDLE
- Confidence: 0.95
- Sources: 1 chunk

---

### Question: "Summarize Jon Mor's entire claim"

**Answer**:
```
Jon Mor's claim, numbered 1, pertains to a rear-end collision 
that occurred on June 6, 2024, at the intersection of 10th Ave 
and 5th St in Sample City. The accident resulted in minor injuries...
```

**Metadata**:
- Route: SUMMARY
- Confidence: 0.85
- Sources: 15 chunks

---

## 🔒 Security Notes

- API key is loaded from `.env` (never hardcoded)
- Read-only access to claims data
- No data modification capabilities
- Local execution only

---

## 🚀 Deployment (Optional)

To share the app:

### Option 1: Streamlit Community Cloud
```bash
# Push to GitHub
git add app/
git commit -m "Add GUI app"
git push

# Deploy on streamlit.io
```

### Option 2: Docker
```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["streamlit", "run", "app/gui_app.py"]
```

---

## 💡 Future Enhancements

Possible additions:
- [ ] Chat history
- [ ] Multiple document support
- [ ] Export answers to PDF
- [ ] Voice input
- [ ] Multi-language support

---

## 📞 Support

If you encounter issues:
1. Check that the main RAG system works: `python main.py`
2. Verify all dependencies are installed
3. Check the terminal for error messages
4. Review the RAG system logs

---

*Simple GUI for Auto Claims RAG System*  
*Built with Streamlit + OpenAI + LlamaIndex*
