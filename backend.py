import io
import os

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

from transform.table_processing import tables_to_dataframe

load_dotenv()

# Azure Form Recognizer credentials
endpoint = os.getenv('AZURE_ENDPOINT')
api_key = os.getenv('AZURE_KEY')
custom_model_id = os.getenv('CUSTOM_AZURE_MODEL_ID')


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
