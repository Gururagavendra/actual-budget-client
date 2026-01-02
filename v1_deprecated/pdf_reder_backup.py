import json
import pymupdf.layout
import pymupdf4llm

def pdf_to_json(pdf):
    doc = pymupdf.open(pdf)

    # Authenticate AFTER opening
    if doc.is_encrypted:
        if not doc.authenticate("guru2111"):
            raise RuntimeError("Wrong PDF password")

    data = pymupdf4llm.to_json(doc)

    # Store the JSON output in a file
    # with open('output.json', 'w') as f:
    #     f.write(data)
    return data

def extract_tables(response):
    header = ["DATE", "MODE", "PARTICULARS", "DEPOSITS", "WITHDRAWALS", "BALANCE"]
    extracted = []
    # count =0
    for page in response["pages"]:
        for block in page.get("boxes", []):
            if block.get("boxclass") == "table":
                rows = block.get('table',[]).get("extract", [])
                print(rows)
                for i, row in enumerate(rows):
                    if row == header:
                        # Take rows after the header
                        table_data = rows[i+1:]
                        extracted.append({
                            "page_number": page["page_number"],
                            "table_rows": table_data
                        })
                        break  # Assuming only one header per table
    # print(count)
    return extracted

def main():
    res_json = pdf_to_json("protected.pdf")
    response = json.loads("output.json")

    extracted = extract_tables(response)

    # Store the extracted tables in a JSON file
    with open('extracted_tables.json', 'w') as f:
        json.dump(extracted, f, indent=4)

    print(extracted)

main()