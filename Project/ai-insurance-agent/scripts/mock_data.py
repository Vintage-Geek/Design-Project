import csv
import random
from datetime import datetime, timedelta

customers = []
for i in range(300):
    name = f"Customer_{i+1}"
    phone = f"+91{random.randint(6000000000, 9999999999)}"
    tz = random.choice(["Asia/Kolkata"] * 25 + ["America/New_York"] * 5)
    customers.append([i+1, name, phone, "en", tz])

policies = []
for i in range(300):
    cust_id = random.randint(1, 300)
    amount = round(random.uniform(1500, 4500), 2)
    due = datetime(2025, 10, 1) + timedelta(days=random.randint(-90, 90))
    status = random.choices(["overdue"]*60 + ["active"]*30 + ["promise_pending"]*10)[0]
    policies.append([i+1, cust_id, amount, due.strftime("%Y-%m-%d"), status, ""])

with open("sample_insurance_data_300.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["customer_id", "name", "phone", "language_pref", "time_zone"])
    writer.writerows(customers)
    writer.writerow([])
    writer.writerow(["policy_id", "customer_id", "premium_amount", "due_date", "status", "promise_date"])
    writer.writerows(policies)

print("Generated sample_insurance_data_300.csv with 300 policies")