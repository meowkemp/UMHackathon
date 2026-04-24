import pandas as pd

# ── 1. Load ──────────────────────────────────────────────
df = pd.read_csv('synthetic_personal_finance_dataset.csv')

print("Original shape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())

# ── 2. Filter Asia only ───────────────────────────────────
df = df[df['region'] == 'Asia']
print("\nAfter Asia filter:", df.shape)

# ── 3. Convert USD → RM ───────────────────────────────────
USD_TO_RM = 4.7
df['monthly_income_rm']   = df['monthly_income_usd']   * USD_TO_RM
df['monthly_expenses_rm'] = df['monthly_expenses_usd'] * USD_TO_RM
df['savings_rm']          = df['savings_usd']          * USD_TO_RM
df['loan_amount_rm']      = df['loan_amount_usd']      * USD_TO_RM  # added
df['monthly_emi_rm']      = df['monthly_emi_usd']      * USD_TO_RM  # added

# ── 4. Fix loan_type nulls ────────────────────────────────
df['loan_type'] = df['loan_type'].fillna('No Loan')

# ── 5. Drop original USD columns ─────────────────────────
df = df.drop(columns=[
    'user_id',
    'record_date',
    'monthly_income_usd',   # replaced by RM version
    'monthly_expenses_usd', # replaced by RM version
    'savings_usd',          # replaced by RM version
    'loan_amount_usd',      # replaced by RM version
    'monthly_emi_usd',      # replaced by RM version
])

# ── 6. Preview final result ───────────────────────────────
print("\nCleaned shape:", df.shape)
print("\nColumns:", df.columns.tolist())
print("\nSample stats:")
print(df[['monthly_income_rm', 'monthly_expenses_rm',
          'savings_rm', 'loan_amount_rm',
          'monthly_emi_rm', 'savings_to_income_ratio']].describe().round(2))

# ── 7. Save cleaned CSV ───────────────────────────────────
df.to_csv('cleaned_finance_data.csv', index=False)
print("\nSaved as cleaned_finance_data.csv")