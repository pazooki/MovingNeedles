import os

current_dir = os.path.dirname(os.path.realpath(__file__))
config = {
    'paths': {
        'data_dir_path': os.path.join(current_dir, 'data'),
        'historical_dir_path': os.path.join(current_dir, 'data', 'historical'),
        'portfolio_file_path': os.path.join(current_dir, 'data', 'portfolio', 'portfolio.json')
    },
    'fees': [4.00],
    'update_frequency_sec': 10,
    'history_live_window': 100,
}