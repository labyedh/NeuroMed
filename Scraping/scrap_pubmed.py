from flask import Flask, request, jsonify, render_template
import requests
import xml.etree.ElementTree as ET

app=Flask(__name__)

@app.route('/')
def index():
    return render_template('Welcome to scraping_papers!')

@app.route('/search', methods=['POST','GET'])
# def search_papers():
#     search_term = request.form.get('term')
#     page = int(request.form.get('page', 1)) if request.form.get('page') else 1
#     print("Search term:", search_term)
#     if not search_term:
#         return jsonify({'error': 'Search term is required'}), 400

#     # Construct the PubMed API URL with the search term and page
#     base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
#     url = f'{base_url}?db=pubmed&term={search_term}&retmode=json&retstart={((page - 1) * 10)}&retmax=10'

#     try:
#         response = requests.get(url)
#         response.raise_for_status()

#         data = response.json()
#         pubmed_ids = data['esearchresult']['idlist']
#         total_results = int(data['esearchresult']['count'])
#         total_pages = (total_results // 10) + 1

#         article_details = []

#         #article details 
#         for pubmed_id in pubmed_ids:
#             summary_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pubmed_id}&retmode=json'
#             summary_response = requests.get(summary_url)
#             summary_response.raise_for_status()

#             summary_data = summary_response.json()
#             article_title = summary_data['result'][pubmed_id]['title']
#             article_url = f'https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/'
#             authors = summary_data['result'][pubmed_id]['authors']
#             author_names = [author['name'] for author in authors]
            
#             # Check if the article is available in PMC
#            # root = ET.fromstring(response.content)
#             article_ids = summary_data['result'][pubmed_id].get('articleids', [])
#         pmcid = None
#         for article_id in root.findall('.//ArticleId'):
#             if article_id.attrib.get('IdType') == 'pmc':
#                 pmcid = article_id.text
#                 break

#             print(f'PMCID: {pmcid}')
#             article_details.append({
#                 'pubmed_id': pubmed_id,
#                 'title': article_title,
#                 'url': article_url,
#                 'authors': author_names,
#                 'pmcid': pmcid
#             })

#             return jsonify({
#                 'articles': article_details,
#                 'total_results': total_results,
#                 'total_pages': total_pages
#             })
#     except requests.exceptions.HTTPError as e:
#         return jsonify({'error':f'An error occurred: {e}'}),500
def search_papers():
    search_term = request.form.get('term')
    page = int(request.form.get('page', 1)) if request.form.get('page') else 1
    print("Search term:", search_term)
    if not search_term:
        return jsonify({'error': 'Search term is required'}), 400

    # Construct the PubMed API URL with the search term and page
    base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
    url = f'{base_url}?db=pubmed&term={search_term}&retmode=json&retstart={((page - 1) * 10)}&retmax=50'

    try:
        # to get the PubMed IDs
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        pubmed_ids = data['esearchresult']['idlist']
        total_results = int(data['esearchresult']['count'])
        total_pages = (total_results // 10) + 1

        article_details = []

        # Retrieve article details 
        for pubmed_id in pubmed_ids:
            summary_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pubmed_id}&retmode=json'
            summary_response = requests.get(summary_url)
            summary_response.raise_for_status()

            summary_data = summary_response.json()
            article_title = summary_data['result'][pubmed_id]['title']
            article_url = f'https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/'
            authors = summary_data['result'][pubmed_id]['authors']
            author_names = [author['name'] for author in authors]
            
            # Check if the article is available in PMC
            article_ids = summary_data['result'][pubmed_id].get('articleids', [])
            pmcid = None
            for article_id in article_ids:
                if article_id['idtype'] == 'pmc':
                    pmcid = article_id['value']
                    break

            print(f'PMCID: {pmcid}')
            article_details.append({
                'pubmed_id': pubmed_id,
                'title': article_title,
                'url': article_url,
                'authors': author_names,
                'pmcid': pmcid
            })

        return jsonify({
            'articles': article_details,
            'total_results': total_results,
            'total_pages': total_pages
        })
    except requests.exceptions.HTTPError as e:
        return jsonify({'error': f'An error occurred: {e}'}), 500
    

@app.route('/abstract/<pubmed_id>')
def abstract(pubmed_id):
    # Construct the PubMed API URL to fetch the abstract
    base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
    url = f'{base_url}?db=pubmed&id={pubmed_id}&retmode=xml'

    try:
        # Make the request to the PubMed API to get the article details
        response = requests.get(url)
        response.raise_for_status()

        # Parse the XML response
        xml_data = response.text
        root = ET.fromstring(xml_data)

        # Find all the abstract elements
        abstract_elements = root.findall('.//AbstractText')

        if abstract_elements:
            abstract = '\n'.join(abstract_element.text.strip() for abstract_element in abstract_elements)
            return jsonify({'abstract': abstract})
        else:
            return jsonify({'abstract': 'Abstract Not Found'})

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
    except ET.ParseError as e:
        return jsonify({'error': 'Error parsing XML response'}), 500
    
@app.route('/full-pdf',methods=['Post'])
def extract_pdf(url): 
    url=request.form.get('url')
    response = requests.get(url)
    if response.status_code == 200:
        # Get the HTML content
        html_content = response.text
        print(html_content)
    else:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")

# @app.route('/source/<pubmed_id>')
# def keywords(pubmed_id):
#     print("Pubmed ID:", pubmed_id)
#     base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
#     url = f'{base_url}?db=pubmed&id={pubmed_id}&retmode=json'
#     try:
#         #Get the article summary
#         response = requests.get(url)
#         response.raise_for_status()

#         # Extract the keywords from the API response
#         data = response.json()
#         print("Data:", data)    
#       #  article_keywords = data['result'][pubmed_id]['keywords']
#         articele_source = data['result'][pubmed_id]['source']
#         print("source:", articele_source)
#         if articele_source:
#             return jsonify({'keywords': articele_source})
#         else:
#             return jsonify({'keywords': 'Keywords Not Found'})

#     except requests.exceptions.RequestException as e:
#         return jsonify({'error': str(e)}), 500
    
    
# @app.route('/fulltext/<pmcid>')
# def fulltext(pmcid):
#     # Construct the PMC API URL to fetch the full text
#     base_url = 'https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi'
#     url = f'{base_url}?id={pmcid}'

#     try:
#         # Make the request to the PMC API to get the full text URL
#         response = requests.get(url)
#         response.raise_for_status()

#         # Parse the XML response
#         root = ET.fromstring(response.content)

#         # Find the full-text URL in the XML
#         full_text_url = None
#         for node in root.findall('.//link'):
#             if node.get('format') == 'pdf':
#                 full_text_url = node.get('href')
#                 break

#         if full_text_url:
#             # Fetch the full text from the URL
#             full_text_response = requests.get(full_text_url)
#             full_text_response.raise_for_status()

#             # Return the full text content
#             return jsonify({'full_text': full_text_response.text})
#         else:
#             return jsonify({'error': 'Full text URL not found'}), 404

#     except requests.exceptions.RequestException as e:
#         return jsonify({'error': str(e)}), 500
#     except ET.ParseError as e:
#         return jsonify({'error': 'Error parsing XML response'}), 500

    
if __name__ == '__main__':
  app.run()