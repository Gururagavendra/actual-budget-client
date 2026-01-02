import pymupdf.layout
import pymupdf4llm

doc = pymupdf.open("protected.pdf")

# Authenticate AFTER opening
if doc.is_encrypted:
    if not doc.authenticate("guru2111"):
        raise RuntimeError("Wrong PDF password")

data = pymupdf4llm.to_json(doc)
# md = pymupdf4llm.to_markdown(doc)
# print(md)
# txt = pymupdf4llm.to_text(doc)
# print(data)

# Store the JSON output in a file
with open('output.json', 'w') as f:
    f.write(data)
