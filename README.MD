
# Django Quick Start

## 1. Create & Activate Virtual Environment

### **Windows**

```bash
python -m venv .env
.env\Scripts\activate
```

### **Linux/macOS**

```bash
python3 -m venv .env
source .env/bin/activate
```

---

## 2. Install requirements

```bash
pip install -r requirements.txt
```

---

## 4. Migrate & Run Server

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Open:
`http://127.0.0.1:8000/`

---

## 5. (Optional) Save Dependencies

```bash
pip freeze > requirements.txt
```

The HTML files are found in `core/app/templates`
dont change logic. just work with classes in the code