import os
import json
import fitz  # PyMuPDF
import pandas as pd
import openai
import streamlit as st
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from io import BytesIO
from PIL import Image
import base64
from backend import CustomDocExtractor

# Load environment variables
load_dotenv('.env')

# Azure OpenAI configurations
AZURE_OPENAI_VERSION = st.secrets.openai_azure.AZURE_OPENAI_VERSION
AZURE_OPENAI_ENDPOINT = st.secrets.openai_azure.AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT = st.secrets.openai_azure.AZURE_OPENAI_DEPLOYMENT
AZURE_OPENAI_API_KEY = st.secrets.openai_azure.AZURE_OPENAI_API_KEY

# Azure Form Recognizer configurations
FR_ENDPOINT = st.secrets.azure_document_intelligence.AZURE_ENDPOINT
FR_KEY = st.secrets.azure_document_intelligence.AZURE_KEY

# Initialize the Document Analysis Client
document_analysis_client = DocumentAnalysisClient(
    endpoint=FR_ENDPOINT, credential=AzureKeyCredential(FR_KEY)
)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Function to convert an image to PDF
def convert_image_to_pdf(image):
    pdf_bytes = BytesIO()  # Create a BytesIO object
    image.save(pdf_bytes, format='PDF')  # Save the image as PDF to bytes
    pdf_bytes.seek(0)  # Move to the beginning of the BytesIO object
    return pdf_bytes.read()  # Return the bytes

# Function to call Azure OpenAI for LLM response and convert to table
def call_azure_openai(document_text, api_version: str, azure_endpoint: str, azure_deployment: str, api_key: str, file_name: str):
    client = openai.AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=azure_endpoint,
        azure_deployment=azure_deployment,
    )
    prompt = f"""
        Extract the following fields from the provided text in JSON format:
        - item_description
        - item_amount (total amount for all quantity)
        - item_subcategory (to which category item belongs if only present for all the items, else NA)
        - item-subcategory-total (subtotal which is present for every sub-category in the invoice, else NA)
        Keep the order as it is in the invoice and do not ignore duplicate values if present
        Text: {document_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )

    response_message = response.choices[0].message.content

    try:
        response_message = json.loads(response_message)
    except json.JSONDecodeError:
        st.write(f'Error decoding response: {response_message}')
        return None

    # Extract the fields from the response and create a table
    items = []
    for item in response_message.get("items", []):  # Assuming items is a list in the response
        item_dict = {
            "file_name": file_name,
            "item-name": item.get("item_description", ""),
            "item-amount": item.get("item_amount", ""),
            "item-subcategory": item.get("item_subcategory", ""),
            "item-sub-category-total": item.get("item_subcategory_total", "")
        }
        items.append(item_dict)

    # Convert to DataFrame
    df = pd.DataFrame(items)
    return df
def display_pdf(file, width=500, height=600):
    # Encode the PDF to base64
    base64_pdf = base64.b64encode(file.getvalue()).decode('utf-8')
    # Display the PDF in an iframe
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="{width}" height="{height}" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


def main():
    # Set the page config for a custom layout
    st.set_page_config(page_title="Invoice Item Extractor", layout="wide")

    st.markdown("""
        <style>
        /* General style */
        .main {
            background-color: #1f1f1f;
            color: #e0e0e0;
            font-family: 'Roboto', sans-serif;
        }
        .header {
            text-align: center;
            padding: 20px;
            color: #00aaff;
        }
        h1 {
            font-weight: 600;
            font-size: 36px;
        }

        /* Styling checkboxes in a single row */
        .stCheckbox > div {
            display: inline-block;
            margin-right: 15px;
        }

        /* Customize buttons */
        button {
            background-color: #00aaff !important;
            color: black !important;
            border-radius: 5px !important;
        }

        /* Customize the data frame */
        .stDataFrame { 
            background-color: #2b2b2b; 
            color: #e0e0e0; 
        }

        /* Hover effect for the file uploader */
        .stFileUploader:hover {
            box-shadow: 0px 0px 15px rgba(0, 170, 255, 0.7);
        }

        /* Modern border */
        .stDataFrame {
            border: 1px solid #00aaff;
        }

        /* Align the additional field checkboxes inline */
        .inline-checkbox {
            display: flex;
            justify-content: flex-start;
            gap: 20px;
            margin-top: 10px;
            margin-bottom: 20px;
        }

        /* Style for headings */
        .blue-heading {
            color: #00aaff;
            font-size: 24px;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("<div class='header'><h1>📄 Invoice Item Extractor</h1></div>", unsafe_allow_html=True)


    # Upload multiple documents
    uploaded_files = st.file_uploader("Upload your documents", type=["pdf", "jpeg", "jpg", "png"], accept_multiple_files=True)

    if uploaded_files:
        # Determine and display heading based on the number of uploaded files
        if len(uploaded_files) == 1:
            st.markdown("<div class='blue-heading'>Extracting information from a Single invoice...</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='blue-heading'>Extracting information from Multiple invoices...</div>", unsafe_allow_html=True)


        # Initialize a list to hold all the extracted data
        all_data = []

        # Loop through the uploaded files
        for uploaded_file in uploaded_files:

            # Process the uploaded file
            if uploaded_file.type == "application/pdf":
                document = uploaded_file.read()
                document_text = extract_text_from_pdf(document)

                # If only one file is uploaded, display the PDF
                if len(uploaded_files) == 1:
                    col1, col2 = st.columns(2)
                    with col1:
                        display_pdf(uploaded_file, width=500, height=600)
            
            else:
                # Handle image files
                image = Image.open(uploaded_file)

                # Convert PNG to JPG if the file is in PNG format
                if uploaded_file.type == "image/png":
                    jpg_bytes = BytesIO()
                    image.convert("RGB").save(jpg_bytes, format="JPEG")
                    jpg_bytes.seek(0)
                    document = jpg_bytes.read()  # Read the bytes as JPG
                else:
                    document = convert_image_to_pdf(image)  # Convert other image types to PDF

                document_text = extract_text_from_pdf(document)

                # If only one file is uploaded, display the image
                if len(uploaded_files) == 1:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.image(image, caption="Uploaded Invoice", use_column_width=True)

            # Analyze using custom extractor
            result, list_of_table_df = CustomDocExtractor().analyze_document(document)
            document_text = result.content

            # Store results in session state
            st.session_state.result = result
            st.session_state.list_of_table_df = list_of_table_df
            st.session_state.document_text = document_text

            # Analyze using Prebuilt Model
            poller = document_analysis_client.begin_analyze_document(
                "prebuilt-invoice", document=document
            )
            prebuilt_result = poller.result()

            # Store Prebuilt result in session state
            st.session_state.prebuilt_result = prebuilt_result

            # Call Azure OpenAI for LLM response
            llm_df = call_azure_openai(
                st.session_state.document_text,
                AZURE_OPENAI_VERSION,
                AZURE_OPENAI_ENDPOINT,
                AZURE_OPENAI_DEPLOYMENT,
                AZURE_OPENAI_API_KEY,
                uploaded_file.name  # Pass the file name
            )

            # Accumulate data into the list
            if llm_df is not None:
                all_data.append(llm_df)

        # Combine all DataFrames into a single DataFrame if there are multiple files
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)

            # Display the combined DataFrame in the second column or full width if more than one file
            if len(uploaded_files) > 1:
                st.write("### Combined Extracted Data")
                st.dataframe(combined_df)
            else:
                
                col2.dataframe(combined_df)

        # Success message after processing all files
        st.success("Extraction completed successfully.")

if __name__ == "__main__":
    main()
