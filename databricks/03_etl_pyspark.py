# Azure Databricks PySpark ETL - PREPARED CLOUD IMPLEMENTATION
# This code mirrors the validated Pandas logic, but the practical package does
# not itself prove that this file was executed successfully in Azure Databricks.
# Only describe Databricks results as executed/tested when separate run evidence exists.

from pyspark.sql import functions as F
import time
import os

STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "REPLACE_WITH_STORAGE_ACCOUNT")
FILE_SYSTEM = os.getenv("ADLS_FILE_SYSTEM", "ecommerce")
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE", "100000"))
INPUT_FILE = os.getenv("INPUT_FILE", f"bronze/ecommerce_{SAMPLE_SIZE}.csv")

BASE = f"abfss://{FILE_SYSTEM}@{STORAGE_ACCOUNT}.dfs.core.windows.net"
INPUT = f"{BASE}/{INPUT_FILE}"
SILVER = f"{BASE}/silver/events_{SAMPLE_SIZE}"
GOLD = f"{BASE}/gold/run_{SAMPLE_SIZE}"

start = time.perf_counter()
raw = spark.read.option("header", True).option("inferSchema", True).csv(INPUT)
raw_count = raw.count()

valid_events = ["view", "cart", "remove_from_cart", "purchase"]
clean = (
    raw.withColumn("event_time", F.to_timestamp("event_time"))
    .withColumn("event_type", F.lower(F.trim(F.col("event_type"))))
    .withColumn("price", F.col("price").cast("double"))
    .dropDuplicates()
    .filter(F.col("event_time").isNotNull())
    .filter(F.col("event_type").isin(valid_events))
    .filter(F.col("product_id").isNotNull() & F.col("user_id").isNotNull() & F.col("user_session").isNotNull())
    .filter(F.col("price") > 0)
    .fillna({"brand": "unknown", "category_code": "unknown"})
    .withColumn("event_date", F.to_date("event_time"))
    .withColumn("event_hour", F.hour("event_time"))
    .withColumn("event_day", F.date_format("event_time", "EEEE"))
    .withColumn("event_month", F.date_format("event_time", "yyyy-MM"))
)
clean_count = clean.count()
clean.write.mode("overwrite").format("parquet").save(SILVER)

# Customer engagement: Score = views + 3*carts + 5*purchases.
engagement_base = clean.groupBy("user_id").agg(
    F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("views"),
    F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("carts"),
    F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
    F.sum(F.when(F.col("event_type") == "remove_from_cart", 1).otherwise(0)).alias("remove_from_cart"),
    F.countDistinct("user_session").alias("sessions"),
    F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0.0)).alias("purchase_value"),
).withColumn(
    "total_interactions",
    F.col("views") + F.col("carts") + F.col("purchases") + F.col("remove_from_cart")
).withColumn(
    "engagement_score",
    F.col("views") + 3 * F.col("carts") + 5 * F.col("purchases")
)
q33, q67 = engagement_base.approxQuantile("engagement_score", [0.33, 0.67], 0.001)
engagement = engagement_base.withColumn(
    "engagement_level",
    F.when(F.col("engagement_score") <= F.lit(q33), F.lit("Low"))
     .when(F.col("engagement_score") <= F.lit(q67), F.lit("Medium"))
     .otherwise(F.lit("High"))
)
engagement.write.mode("overwrite").format("parquet").save(f"{GOLD}/customer_engagement")

# Ordered session funnel: View -> Cart -> Purchase using first event timestamps.
stage_times = clean.groupBy("user_session").agg(
    F.min(F.when(F.col("event_type") == "view", F.col("event_time"))).alias("first_view"),
    F.min(F.when(F.col("event_type") == "cart", F.col("event_time"))).alias("first_cart"),
    F.min(F.when(F.col("event_type") == "purchase", F.col("event_time"))).alias("first_purchase"),
).withColumn("has_view", F.col("first_view").isNotNull().cast("int")) \
 .withColumn("reached_cart", (F.col("first_view").isNotNull() & F.col("first_cart").isNotNull() & (F.col("first_cart") >= F.col("first_view"))).cast("int")) \
 .withColumn("reached_purchase", (F.col("first_view").isNotNull() & F.col("first_cart").isNotNull() & F.col("first_purchase").isNotNull() & (F.col("first_cart") >= F.col("first_view")) & (F.col("first_purchase") >= F.col("first_cart"))).cast("int"))

counts = stage_times.agg(
    F.sum("has_view").alias("view_sessions"),
    F.sum("reached_cart").alias("cart_sessions"),
    F.sum("reached_purchase").alias("purchase_sessions"),
).first()
view_sessions = int(counts["view_sessions"] or 0)
cart_sessions = int(counts["cart_sessions"] or 0)
purchase_sessions = int(counts["purchase_sessions"] or 0)
def rate(n, d):
    return float(n / d * 100.0) if d else 0.0
funnel = spark.createDataFrame([
    (1, "View sessions", view_sessions, rate(view_sessions, view_sessions), 100.0),
    (2, "Cart sessions", cart_sessions, rate(cart_sessions, view_sessions), rate(cart_sessions, view_sessions)),
    (3, "Purchase sessions", purchase_sessions, rate(purchase_sessions, view_sessions), rate(purchase_sessions, cart_sessions)),
], ["stage_order", "stage", "sessions", "percent_of_view_sessions", "conversion_from_previous_stage_pct"])
funnel.write.mode("overwrite").format("parquet").save(f"{GOLD}/conversion_funnel")

# Cart abandonment by session + category. remove_from_cart is reported but does
# not independently determine abandonment.
sc = clean.groupBy("user_session", "category_code").agg(
    F.max(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("had_cart"),
    F.max(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("had_purchase"),
    F.sum(F.when(F.col("event_type") == "remove_from_cart", 1).otherwise(0)).alias("remove_from_cart_events"),
)
abandonment = sc.groupBy("category_code").agg(
    F.sum("had_cart").alias("cart_sessions"),
    F.sum(F.when((F.col("had_cart") == 1) & (F.col("had_purchase") == 0), 1).otherwise(0)).alias("abandoned_sessions"),
    F.sum("remove_from_cart_events").alias("remove_from_cart_events"),
).withColumn(
    "abandonment_rate_pct",
    F.when(F.col("cart_sessions") > 0, F.col("abandoned_sessions") / F.col("cart_sessions") * 100).otherwise(0.0)
)
abandonment.write.mode("overwrite").format("parquet").save(f"{GOLD}/cart_abandonment")

# Category performance. Revenue is sum(price) on purchase events; there is no quantity field.
category = clean.groupBy("category_code").agg(
    F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("views"),
    F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("cart_additions"),
    F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
    F.sum(F.when(F.col("event_type") == "remove_from_cart", 1).otherwise(0)).alias("remove_from_cart_events"),
    F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0.0)).alias("purchase_revenue"),
).withColumn(
    "view_to_cart_rate_pct",
    F.when(F.col("views") > 0, F.col("cart_additions") / F.col("views") * 100).otherwise(0.0)
).withColumn(
    "purchase_conversion_rate_pct",
    F.when(F.col("views") > 0, F.col("purchases") / F.col("views") * 100).otherwise(0.0)
)
category.write.mode("overwrite").format("parquet").save(f"{GOLD}/category_performance")

# These become genuine Azure scalability measurements only if this code is
# actually executed on Databricks for the controlled workloads and run evidence is retained.
elapsed = time.perf_counter() - start
perf = spark.createDataFrame([(
    SAMPLE_SIZE, raw_count, clean_count, float(elapsed), float(clean_count / elapsed if elapsed else 0)
)], ["sample_size", "raw_rows", "clean_rows", "processing_seconds", "throughput_rows_per_sec"])
perf.write.mode("append").format("parquet").save(f"{BASE}/gold/pipeline_performance")

print("DATABRICKS ETL RUN COMPLETED")
print(f"Input: {INPUT}")
print(f"Raw rows: {raw_count:,}")
print(f"Clean rows: {clean_count:,}")
print(f"Processing time: {elapsed:.2f} seconds")
print(f"Throughput: {clean_count/elapsed:,.2f} rows/sec")
