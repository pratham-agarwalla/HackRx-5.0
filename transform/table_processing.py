import pandas as pd
from azure.ai.formrecognizer import DocumentTable, DocumentTableCell
from typing import List
Row = List[DocumentTableCell]
RawTable = List[Row]


def group_table_by_rows(table: DocumentTable) -> RawTable:
    cells = sorted(table.cells, key=lambda cell: (cell.row_index, cell.column_index))
    curr_row_idx = cells[0].row_index

    rows = []
    curr_row = []
    for cell in cells:
        if cell.row_index != curr_row_idx:
            rows.append(curr_row)
            curr_row = []
            curr_row_idx = cell.row_index
        curr_row.append(cell)
    if curr_row:
        rows.append(curr_row)

    return rows

def clean_cell_content(content: str) -> str:
    return content.replace(':unselected:', '').strip()

def extract_table_title(raw_table) -> str:
    if len(raw_table[0]) == 1:
        return raw_table[0][0].content
    else:
        return None

def has_table_title(raw_table) -> bool:
    if len(raw_table[0]) == 1:
        return True
    else:
        return False

def tables_to_dataframe(tables: List) -> List[pd.DataFrame]:
    if not tables:
        return pd.DataFrame()

    raw_tables = list(map(group_table_by_rows, tables))
    
    #return raw_tables
    list_of_pandas_df = []
    list_of_table_titles = []
    for raw_table in raw_tables:
        try:
            list_of_table_titles.append(extract_table_title(raw_table))
            if has_table_title(raw_table):
                raw_table = raw_table[1:]
            
            for i, row in enumerate(raw_table):
                row_content = [clean_cell_content(cell.content) for cell in row]
                if i == 0:
                    df_table = pd.DataFrame(columns=row_content)
                else:
                    df_table.loc[i-1] = row_content
            list_of_pandas_df.append(df_table)
        except Exception as e:
            pass
        
    return zip(list_of_table_titles, list_of_pandas_df)