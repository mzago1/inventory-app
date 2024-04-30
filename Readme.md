# Serverless Inventory Management -

## Goals

- **Learn skills relevant to our job**
- Gain an understanding of and practical experience using the serverless architecture paradigm
- Gain an understanding of and practical experience using infrastructure as code
- Learn how to work with JSON and CSV data
- Learn how to design for and build with ephemeral compute resources (e.g. Lambda Functions)
- Learn how to build and deploy long-running compute resources (e.g. Docker Containers/ EC2 instances)
- Learn how to design and use NoSQL data structures
- Learn how to design and build event driven architectures and computing solutions
- Learn how to build and design decoupled architectures using different integration patterns

## Scenario

You're working for a company that needs a new inventory management solution for their various warehouses.
For various reasons they prefer a serverless implementation.
One of these reasons being that they don't want to pay for long running compute infrastructure.

The basic idea is very simple.
Every few minutes an inventory update file is created, which contains transactions for items in stock.
The inventory file is a CSV file, where each column is delimited by a TAB.
It looks like this:

| **Timestamp** | **WarehouseName** | **ItemId** | **ItemName** | **StockLevelChange** |
| --- | --- | --- | --- | --- |
| 2021-02-15T12:00:00.000+01:00 | Berlin 1 | a123v5 | tecRacer T-Shirt | -3 |
| 2021-02-15T12:00:01.000+01:00 | Bremen 4 | d23x56 | tecRacer tecPert Sticker | 4 |
| 2021-02-15T13:30:00.000+01:00 | Aachen 1 | r345v7 | Kaffeebohnen | -30 |
| 2021-02-15T15:00:00.000+01:00 | Borkum 1 | g45678 | AWS Sticker | 500 |
| 2021-02-15T16:17:00.000+01:00 | Berlin 2 | j5yc89 | Book of tecRacer | 70 |

About the format:

- the `Timestamp` column holds an ISO8601 formated timestamp of the point in time when the transaction happened
- the `WarehouseName` column contains information on the warehouse in which this transaction happened
- the `ItemId` holds a unique identifier for each item, this is a string
- the `ItemName` is a human readable description of the item
- the `StockLevelChange` column indicates with a number if items have been added to the inventory (positive number) or removed (negative number)

These inventory files will be uploaded into an S3 bucket with a object key that looks like this:

```text
/inventory_files/<year>/<month>/<day>/<yyyymmddHHMMSS>_inventory.csv
```

This company also needs to restock items if stock levels are getting below a certain threshold and this restocking threshold depends on the aforementioned `ItemId`.
Occasionally (at most once per day) there will be an update to these restocking thresholds based on the current supply market conditions.
Changes to the threshold will be delivered via JSON in this format:

```json
{
    "ThresholdList": [
        {
            "ItemId": "a123v5",
            "RestockIfBelow": 25
        },
        {
            "ItemId": "g45678",
            "RestockIfBelow": 200
        }
    ]
}
```

These restock threshold updates are also stored in an S3 bucket under a key that looks like this:

```text
/restock_thresholds/<year>/<month>/<day>/restock_thresholds.json
```

> **Note:** There won't be specific restock thresholds in all cases. If there are none, it should be assumed to be **10**.

Whenever an item's stock falls below the currently set threshold, we want to send an E-Mail notification to the purchasing department to buy more items.

Management also wants to be able to get some reports on demand, which should be created on demand by the system in a reasonable time span.

The company also has a long running batch job, that is supposed to download and validate all inventory files of the day.
This batch job needs to process the inventory files in the sequence they arrived in (best effor ordering is sufficient).
It will usually run for about 40-50 minutes and needs to be a continuous process that gets started at 3 am.

## Prerequisites

- An AWS Account
- A diagram tool such as LucidChart
- A colleague to talk to
- Python >= 3.7

## Preparations

Use the provided script (`data_generator.py`) to create some sample data for this use case.
Check out the parameters in the documentation, you can use them to create more data to test your code.

## Tasks

> **Important:**
>
> There is no **best** solution here, all solutions have trade-offs and it's okay to iterate over them multiple times.
> Feel free to start with a solution that uses technologies you already know and then continue iterating to make the solution use more serverless components.

### Task 01: Getting started: Initial Planning and choice of weapons

It's not the goal to come up with a perfect solution in the beginning, but having a good idea of what you're trying to implement helps with the next steps.

1. Read and think about the scenario **and all tasks**, make a list of all requirements
1. Design an architecture diagram for this use case and explain it to a colleague
1. Design a data model that's fit for the use case and also explain that to a colleague
1. Iterate over the design until you have a good mental model how the data flows are supposed to look like
1. Select an infrastructure as code framework, the choice may depend on your preferences or what your colleagues use
    - If you're familiar with object oriented programming in Python, TypeScript, .Net, Java or JavaScript I strongly recommend the Cloud Development Kit
    - If your background is more related to a traditional sysops role, you might prefer declarative solutions such as Terraform, the Serverless Framework, SAM or pure CloudFormation

### Task 02: Implement data ingestion for the inventory files

1. Create the infrastructure to store the inventory files
1. Implement a mechanism to respond to new inventory files, parse them and update the stock levels
1. Test this with some of the sample data you created earlier

### Task 03: Implement data ingestion for the restock thresholds

1. Create the infrastructure to store the restock thresholds, ideally it's the same bucket as in Task 02
1. Implement a mechanism to respond to new files, parse them and update the restock levels
1. Test this with some of the sample data

### Task 04: Implement alerting logic based on the restock thresholds

Whenever updates to the stock levels happen, it should be checked if they're below the restock level for that item.
If no restock level exists for this item, it should be assumed to be **10**.
Should that item be below the restock level, send a notification to the purchasing department (your e-mail inbox) to request new items.

### Task 05: Implement reporting requirements

As mentioned in the scenario, management has a few requirements in terms of reporting.

They want to:

- Get a list of all items in warehouse `x`
- Get a list of all items in warehouse `x` with a current inventory that's greater than `y`
- Get the total inventory for item with id `x` across all warehouses

Implement code to fulfill these requirements.

### Task 06: Implement daily batch for data validation

As mentioned in the scenario, there is a requirement to periodically check all transaction files/inventory updates since the last check for inconsistencies.
This is a computationally expensive task, that takes a while.
It has to be done for each transaction, ideally in the order in which they appeared and can't be parallelized.
The transactions need to be checked daily and 3 am in UTC time has been selected as a start time.
Since these checks typically take between 40-50 minutes, a solution that's a long running process is required.

**Check logic:**

- For each file since the last check
  - Download the file and parse it
  - For each transaction in the file `check_transaction`

    ```python
    def check_transaction(*args, **kwargs):
        """Long and complex check for each transaction"""
        import time
        time.sleep(10) # "Process" for 10 seconds. You may lower this for debugging.
    ```

- Send an E-Mail notification, that the validation has been completed

Implement a solution that fulfills these requirements.

### Task 07 (optional): Refactor data model to adhere to a single table design

_This is an advanced task if you want to dive deeper in DynamoDB which I highly recommend._

You've presumably created multiple tables in DynamoDB to implement your architecture.
This can be optimized, check out the re:invent talks by Rick Houlihan (DynamoDB 400 level talks) - yes, all of them, they're amazing - and after you've watched them, reconsider and redesign your table(s).

### Task 08 (optional): Apply new restock thresholds to existing items

_This is a task that may be suitable to learn how to **step** up your **function** game._

The scenario asks you to apply new restock thresholds after they have been send to the system.
The most straightforward implementations will have the problem, that these changes to the threshold are only taken into account, whenever there is a transaction that changes the stock level.

**Example:**

1. Current stock of `x` is 5 and the restock threshold is 2
1. New restock thresholds come in, the threshold for `x` is now 10
1. Now `x` would need to be restocked
1. If you only evaluate if restocks need to happen whenever the stock level of `x` changes, this won't be discovered until the stock level changes

Implement a way to check current inventory levels against the new restock thresholds.

### Task 09 (optional): A wild data scientist appears

You've just got a new addition to the team - a data scientist!
This data scientist would like to do exploratory analyses on the raw data using SQL.

Can you help him out and set up serverless infrastructure for them to query the data?

### Task 10 (optional): Dance like nobody is watching, encrypt like everybody is

It's good practice to encrypt data at rest and in transit.
The in transit part is typically handled through the AWS SDK automatically.
Encryption at rest depends on the service and usually works in combination with AWS KMS.

