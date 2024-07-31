import pandas as pd
from numpy import random


def load_meta_info_from_excel(file_path, sheet2renames):
    dict_df = {}
    for sheet in sheet2renames:
        df = pd.read_excel(file_path, sheet_name=sheet, header=2).dropna(thresh=1) #drop empty rows
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')] #drop empty columns
        dict_df[sheet2renames[sheet]] = df
    return dict_df


def load_response_data(file_path, sample_pct=None):
    if sample_pct is None:
        rows_skipped = None
    elif 0.0 < sample_pct < 1.0:
        rows_skipped = lambda i: i>0 and random.random() > sample_pct
    else:
        raise ValueError(f'To enable sampling methods, please provide sample size between (0, 1]')

    df = pd.read_csv(file_path, header=0, engine='python', skiprows=rows_skipped)
    return df


def get_variable_definition(lookup, var):
    try:
        return lookup.loc[lookup['Variable'] == var, 'Label'].values[0]
    except:
        raise ValueError(f'{var} is not defined in lookup table!')
        

def get_var_value_mapping(lookup, var):
    try:
        var_mapping = lookup.loc[lookup['Variable name'] == var]
        return dict(zip(var_mapping['Variable Values'], var_mapping['Label'].astype(str)))
    except:
        raise ValueError(f'{var} has no value mapping in lookup table!')
        
