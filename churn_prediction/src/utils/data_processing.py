import pandas as pd
from numpy import nan


def create_binary_label(val, accept_pos):
    if pd.isnull(val):
        return 1
    elif val in accept_pos:
        return 0
    else:
        return 1


def convert_column_value(df, col_type_mapping):
    for col in col_type_mapping:
        df[col] = df[col].replace(r'^\s*$', nan, regex=True)
        df[col] = pd.to_numeric(df[col], errors='coerce').astype(col_type_mapping[col])
    return df


def get_top_n_var_vals(df, var, topn=None):
    df_count = df.groupby(var).size().reset_index()
    df_count.columns = [var, 'count']
    df_count.sort_values('count', ascending=False, inplace=True)
    if topn:
        df_count = df_count.head(topn)
    return df_count[var].to_list()

