import pandas as pd
import glob
import os

def load_hinge_sheet(folder):
    files = glob.glob(os.path.join(folder, "*Door Data*.xlsx"))
    if not files:
        return None
    file = max(files, key=os.path.getmtime)
    df = pd.read_excel(file)
    df["Height"] = df["Leaf size"].str.split("x").str[0].astype(int)
    df["Width"] = df["Leaf size"].str.split("x").str[1].astype(int)
    return df
