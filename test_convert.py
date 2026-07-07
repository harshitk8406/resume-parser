"""
Test: feed the HAIRAT PDF back through the converter pipeline.
Generates test_output.docx — open in Word to compare with the PDF.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import fitz
from converter import generate_docx

# Extract text from the HAIRAT PDF
doc = fitz.open(r'HAIRAT - Salesforce BA - Copy.pdf')
full_text = "\n".join(page.get_text("text") for page in doc)

# Feed through agent's convert_resume (uses Groq)
from agent import convert_resume
print("Calling Groq to convert HAIRAT PDF text...")
data = convert_resume(full_text)

print("Name:", data.get("name"))
print("Skills:", len(data.get("technical_skills", [])))
print("Experience:", len(data.get("professional_experience", [])))
print("Certifications:", len(data.get("certifications", [])))

# Build DOCX
docx_bytes = generate_docx(data)
with open("test_output.docx", "wb") as f:
    f.write(docx_bytes)

print(f"\nDone! Saved test_output.docx ({len(docx_bytes)//1024} KB)")
print("Open this file in Word and compare it to the HAIRAT PDF.")
