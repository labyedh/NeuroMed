import requests
import xml.etree.ElementTree as ET
import json

# Function to remove XML namespace
def remove_namespace(xml_text):
    return xml_text.replace(' xmlns="http://www.w3.org/2005/Atom"', "")

papers = []
batch_size = 1000  # Number max recommandé par ArXiv
total_results = 5000  # Nombre total de résultats souhaité

for start in range(0, total_results, batch_size):
    url = f"https://export.arxiv.org/api/query?search_query=cancer&start={start}&max_results={batch_size}"
    response = requests.get(url)
    xml_cleaned = remove_namespace(response.text)
    root = ET.fromstring(xml_cleaned)

    for entry in root.findall("entry"):
        # Extract PDF link from <link> with rel="related"
        pdf_link = None
        for link in entry.findall("link"):
            if link.attrib.get("rel") == "related" and link.attrib.get("type") == "application/pdf":
                pdf_link = link.attrib.get("href")
                break

        paper = {
            "title": entry.find("title").text,
            "authors": [author.find("name").text for author in entry.findall("author")],
            "abstract": entry.find("summary").text,
            "doi": entry.find("id").text,
            "url": entry.find("id").text,
            "pdf_url": pdf_link  # Add PDF link to the paper data
        }
        papers.append(paper)

    print(f"Fetched {len(papers)} papers so far...")

# Save to JSON
with open("arxiv_papers_with_pdf.json", "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=4, ensure_ascii=False)

print(f"Saved {len(papers)} papers to arxiv_papers_with_pdf.json")
