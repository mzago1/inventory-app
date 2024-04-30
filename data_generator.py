import collections
import csv
import hashlib
import itertools
import json
import os
import pathlib
import random
import typing

from datetime import datetime, timedelta

DIR_INVENTORY_FILES = os.path.join(os.path.dirname(__file__), "inventory_files")
DIR_RESTOCK_THRESHOLDS = os.path.join(os.path.dirname(__file__), "restock_thresholds")

PRODUCT_BRAND_NAMES = ["Google", "Apple", "Microsoft", "Samsung", "LG", "Oracle", "SAP"]
PRODUCT_CATEGORIES = ["Phone", "Calculator", "TV", "Car", "Headphone", "Fridge", "Rock", "Watch"]
PRODUCT_VERSIONS = ["1", "2", "3S", "I", "IV", "II", "S", "Pro", "Pro Max", "Mini", "NG", "Plus"]

WAREHOUSES = ["BERLIN I", "FRANKFURT I", "HANNOVER I", "HANNOVER II", "HAMBURG I", "DUISBURG I"]

AMOUNT_OF_PRODUCTS = 1000
AMOUNT_OF_TRANSACTIONS = 100_000
AMOUNT_OF_THRESHOLD_UPDATES = 20
AMOUNT_OF_THRESHOLD_UPDATES_PER_FILE = 40

def product_generator(n: int) -> typing.List[str]:
    """
    Returns a list of product names with length n.

    Args:
        n (int): The number of product names to generate

    Returns:
        typing.List[str]: List of product names, entries are unique.
    """

    all_products = list(
        itertools.product(PRODUCT_BRAND_NAMES, PRODUCT_CATEGORIES, PRODUCT_VERSIONS)
    )

    random.shuffle(all_products)

    return [ " ".join(product) for product in all_products[:n]]

def create_directories_if_not_exist() -> None:
    """
    Creates the output directories if they don't exist yet.
    """
    pathlib.Path(DIR_INVENTORY_FILES).mkdir(parents=True, exist_ok=True)
    pathlib.Path(DIR_RESTOCK_THRESHOLDS).mkdir(parents=True, exist_ok=True)

def create_random_transactions(n: int) -> typing.List[int]:

    # We need to start at some positive value
    starting_point = random.randint(0, 10)

    transactions = [starting_point]
    current_level = starting_point
    for _ in range(n):
        transaction = random.randint( - current_level, 20)
        current_level += transaction
        transactions.append(transaction)
    
    return transactions

def create_transactions(product_names: typing.List[str], n: int) -> dict:
    
    transactions = collections.defaultdict(dict)

    for product_name in product_names:
        for warehouse in WAREHOUSES:
            transactions_for_warehouse = create_random_transactions(n)
            transactions[product_name][warehouse] = transactions_for_warehouse

    return transactions

def create_transaction_stream(transactions: dict, max_num: int=-1):

    timestamp = datetime.now()
    number_of_transactions = 0

    while True:
        product: str = random.choice(list(transactions.keys()))
        product_id: str = hashlib.sha256(product.encode("utf-8")).hexdigest()
        warehouse: str = random.choice(list(transactions[product].keys()))
        transaction_value: int = transactions[product][warehouse].pop(0)
        timestamp += timedelta(seconds=random.randint(1, 40))

        if len(transactions[product][warehouse]) == 0:
            # Remove the warehouse whose transactions have been exhausted
            del transactions[product][warehouse]
        
        if len(transactions[product].keys()) == 0:
            # Remove the product whose transactions have been exhausted
            del transactions[product]
        
        number_of_transactions += 1
        yield [timestamp.isoformat()+"Z", warehouse, product_id, product, transaction_value]

        if max_num != -1 and number_of_transactions >= max_num:
            break

        if len(transactions.keys()) == 0:
            break
    
def write_batch(batch_of_transactions: typing.List[list]):
    
    last_timestamp = batch_of_transactions[-1][0]
    year, month, day = last_timestamp.split("T")[0].split("-")

    file_name = last_timestamp[:16].replace("T", "").replace("-", "").replace(":", "") + "_inventory.csv"

    # Create the file path if it doesn't exist.
    file_path = f"{DIR_INVENTORY_FILES}/{year}/{month}/{day}/"
    pathlib.Path(file_path).mkdir(parents=True, exist_ok=True)

    with open(file_path + file_name, mode="w", newline="") as inventory_file:
        writer = csv.writer(inventory_file, delimiter=";")

        writer.writerow(["Timestamp", "WarehouseName", "ItemId", "ItemName", "StockLevelChange"])

        for transaction in batch_of_transactions:
            writer.writerow(transaction)

def create_transaction_files(transactions: dict):
    start_prefix = ""
    batch = []

    for transaction in create_transaction_stream(transactions, AMOUNT_OF_TRANSACTIONS):

        current_prefix = transaction[0][:13] # Select the part including the hour

        if current_prefix != start_prefix:
            start_prefix = current_prefix
            if len(batch) != 0:
                write_batch(batch)
            batch = []
        
        batch.append(transaction)
    
    # Write the last batch
    if len(batch) != 0:
        write_batch(batch)

def create_thresholds(product_list: typing.List[str]) -> dict:
    
    thresholds = {}

    for product in product_list:

        product_id = hashlib.sha256(product.encode("utf-8")).hexdigest()

        threshold_updates = [random.randint(5, 50) for _ in range(AMOUNT_OF_THRESHOLD_UPDATES)]

        thresholds[product_id] = threshold_updates

    return thresholds

def create_threshold_stream(thresholds: dict, max_num: int):
    
    number_of_updates = 0

    timestamp = datetime.now()

    while True:

        threshold_updates = {}

        for _ in range(AMOUNT_OF_THRESHOLD_UPDATES_PER_FILE):
            product_id = random.choice(list(thresholds.keys()))

            # We don't really care if there are duplicates, just overwrite them
            threshold_updates[product_id] = thresholds[product_id].pop(0)
        
        update_batch = {
            "ThresholdList": [
                {"ItemId": product_id, "RestockIfBelow": value} \
                    for product_id, value in threshold_updates.items()
            ]
        }


        year, month, day = timestamp.isoformat().split("T")[0].split("-")
        file_path = f"{DIR_RESTOCK_THRESHOLDS}/{year}/{month}/{day}/"
        pathlib.Path(file_path).mkdir(parents=True, exist_ok=True)

        file_name = file_path + "restock_thresholds.json"

        with open(file_name, "w") as output_file:
            json.dump(update_batch, output_file, indent=4)

        number_of_updates += 1
        timestamp += timedelta(days=random.randint(1,2))

        if number_of_updates >= max_num:
            break


def main():
    random.seed(7)  # Making this consistent

    create_directories_if_not_exist()

    product_list = product_generator(AMOUNT_OF_PRODUCTS)

    transactions = create_transactions(
        product_list,
        # We want a roughly equal distribution of transactions/item
        int(AMOUNT_OF_TRANSACTIONS/AMOUNT_OF_PRODUCTS) + 10
    )

    create_transaction_files(transactions)

    thresholds = create_thresholds(product_list)

    create_threshold_stream(thresholds, AMOUNT_OF_THRESHOLD_UPDATES)

if __name__ == "__main__":

    main()