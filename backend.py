import io
import os
import streamlit as st


from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

from transform.table_processing import tables_to_dataframe

load_dotenv()

# Azure Form Recognizer credentials
endpoint = st.secrets.azure_document_intelligence.AZURE_ENDPOINT
api_key = st.secrets.azure_document_intelligence.AZURE_KEY
custom_model_id = st.secrets.azure_document_intelligence.CUSTOM_AZURE_MODEL_ID


class CustomDocExtractor:
    def __init__(self):
        # Initialize the Document Analysis Client
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )

    def analyze_document(self, document_data: bytes):
        with io.BytesIO(document_data) as document_stream:
            poller = self.document_analysis_client.begin_analyze_document(custom_model_id, document_stream)
            result = poller.result()
            list_of_extracted_tables = result.tables
            list_of_table_df = tables_to_dataframe(list_of_extracted_tables)
        return [result, list_of_table_df]
