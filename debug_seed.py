import pandas as pd
from src.services.google_sheets import DatabaseManager
from dashboard.building_store import load_energy_dataset

df = load_energy_dataset()

print('Loaded dataset:')
print(f'  Buildings: {list(df["building_id"].unique())}')
print(f'  Total rows: {len(df)}')

buildings = df['building_id'].unique()
initial_data = []

for building in buildings:
    building_rows = df[df['building_id'] == building].head(5)
    initial_data.append(building_rows)

initial_data = pd.concat(initial_data, ignore_index=True)

print('\nSeeding logic results:')
print(f'  Total initial rows: {len(initial_data)}')
print(f'  Buildings: {list(initial_data["building_id"].unique())}')
print(f'  Per-building count: {initial_data.groupby("building_id").size().to_dict()}')