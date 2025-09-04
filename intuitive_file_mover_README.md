# 🚀 Intuitive File Mover

A sleek, terminal-based file moving utility that makes organizing your files effortless. Navigate directories with arrow keys, search intelligently, and move files with confidence through a clean, intuitive interface.

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)


<img width="405" height="270" alt="Screenshot 2025-09-04 at 09 11 02" src="https://github.com/user-attachments/assets/99c6f302-e857-41bd-b932-7ce0be8db7b6" />
<img width="405" height="270" alt="Screenshot 2025-09-04 at 09 12 24" src="https://github.com/user-attachments/assets/0c029c5a-88dd-4c3e-8324-5c0937e420da" />
<img width="405" height="270" alt="Screenshot 2025-09-04 at 09 12 48" src="https://github.com/user-attachments/assets/5c2d3a11-0292-47b6-b879-50bea3ff9e23" />
<img width="405" height="270" alt="Screenshot 2025-09-04 at 09 12 58" src="https://github.com/user-attachments/assets/b18a351c-ae89-47c2-8f3a-6d7011526d8b" />
<img width="405" height="270" alt="Screenshot 2025-09-04 at 09 13 18" src="https://github.com/user-attachments/assets/099b55d1-6512-42d0-8401-f773919b5e28" />
<img width="405" height="270" alt="Screenshot 2025-09-04 at 09 13 30" src="https://github.com/user-attachments/assets/58564798-45a6-4e56-9121-eb6d2c8d7232" />

## ✨ Features

### 🎯 **Intuitive Navigation**
- **Arrow key navigation** through directories - feels like a native terminal tool
- **Visual breadcrumbs** showing your current location
- **Parent directory traversal** with easy ".." navigation
- **Starting point** defaults to your home directory

### 🔍 **Smart Search**
- **Local directory search** - find folders anywhere in your current directory tree
- **File search within directories** - quickly locate specific files
- **Real-time matching** with predictable results (no fuzzy matching weirdness)
- **Intelligent scoring**: exact matches → starts with → contains

### 📁 **File Operations**
- **Multi-select files** with spacebar and arrow keys
- **File size display** for easy identification
- **Move preview table** showing exactly what will happen
- **Conflict resolution** for duplicate filenames
- **Safe operation validation** prevents moving files to the same location

### 🎨 **Beautiful Interface**
- **Rich terminal formatting** with colors and panels
- **Clean, professional appearance** without being overwhelming
- **Progress indicators** during directory indexing
- **Clear success/error feedback**

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Install Dependencies and run

```bash
pip install rich inquirer
python3 intuitive_file_mover.py
