from os import makedirs, path


#########
# LOCAL SETUPS
#########
RANDOM_SEED = 42
MODEL_ROOT_DIR = "/libs/src/models"
DATA_ROOT_DIR = "/libs/src/data"
makedirs(MODEL_ROOT_DIR, exist_ok=True)
makedirs(DATA_ROOT_DIR, exist_ok=True)

#########
# INPUT FILES
#########
fname_survey_data = path.join(DATA_ROOT_DIR, 'CRT Global File Churn_test.csv')
fname_code_book = path.join(DATA_ROOT_DIR, 'Codebook.xlsx')
fname_country_continent = path.join(DATA_ROOT_DIR, 'country_continent_mapping.csv')


########
# OTHER VARIABLES
########
COL_ID = 'CODERESP'
RESPONSE_COLS_MAPPING = {
    'id': [COL_ID],
    'demographic': ['COUNTRY', 'continent', 'Industry', 'Company', 'Gender', 'Age', 'Region', 'Income', 'Education', 'OCCUPATION'],
    'feedback': ['Familiarity', 'Q600C', 'Q600D', 'Q600_0'],
    'answers': ['Q600_4', 'Q600_6', 'Q600_10', 'Q600_14', 'Q600_16', 'Q600_17', 'Q600_18', 'Q600_19', 'Q600_20', 'Q600_21', 'Q600_22', 'Q600_23', 'Q600_24', 'Q600_25', 'Q600_30', 'Q600_31', 'Q600_32', 'Q600_98', 'Q600_99', 'Q600_33'],
    'others': ['Pulse_G_Reb', 'Weight_Final', 'Month']
}
PRED_VAL_MAPPING = {0: 'Not Churn', 1: 'Churn'}
TEST_SIZE = 0.2