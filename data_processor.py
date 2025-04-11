import pandas as pd
from datetime import datetime
import os
from config import DATA_DIR

def compare_dataframes(old_df, new_df):
    if old_df is None:
        return new_df, True
    
    if new_df is None:
        return None, False
        
    if set(old_df.columns) != set(new_df.columns):
        print("⚠️ Warning: Dataframes have different columns")
        return new_df, True
    
    old_df = old_df.reset_index(drop=True)
    new_df = new_df.reset_index(drop=True)
    
    if old_df.equals(new_df):
        return None, False
    
    changed_rows = pd.concat([new_df, old_df]).drop_duplicates(keep=False)
    
    return changed_rows, True

def save_data(df, timestamp):
    if df is not None and not df.empty:
        filename = f"vaxtor_data_{timestamp}"
        df.to_csv(f"{DATA_DIR}/{filename}.csv", index=False)
        df.to_json(f"{DATA_DIR}/{filename}.json", orient="records", indent=2)
        return True
    return False

def should_process_plate_recognition(row_data, force_recognition=False):
    if force_recognition:
        return True
        
    is_make_missing = pd.isna(row_data.get('Make')) or str(row_data.get('Make')).strip() == ''
    is_model_missing = pd.isna(row_data.get('Model')) or str(row_data.get('Model')).strip() == ''
    
    return is_make_missing or is_model_missing 