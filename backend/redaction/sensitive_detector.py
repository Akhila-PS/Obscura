import re

patterns = {
    "Phone Number": r"\b\d{10}\b",
    "Email Address": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
    "Aadhaar Number": r"\b\d{4}\s\d{4}\s\d{4}\b"
}

def detect(text):
    for label, pattern in patterns.items():
        if re.search(pattern, text):
            return label
    return None
