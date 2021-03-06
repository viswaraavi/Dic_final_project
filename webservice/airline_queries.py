import sys
import os
import json
import re
import pickle
import time
from datetime import date

os.environ['SPARK_HOME'] = "/usr/lib/spark"
sys.path.append("/usr/lib/spark/python")
sys.path.append("/usr/lib/spark/python/lib/py4j-0.10.3-src.zip")

try:
    from pyspark import SparkContext
    from pyspark import SparkConf
    from pyspark.sql import HiveContext
    from pyspark.sql import SparkSession
    from pyspark.sql.types import *
    from pyspark.mllib.tree import RandomForest, RandomForestModel
    from pyspark.mllib.util import MLUtils
except ImportError as e:
    print ("error importing spark modules", e)
    sys.exit(1)

spark = SparkSession.builder \
    .appName("DIC FINAL PROJECT") \
    .enableHiveSupport() \
    .config("spark.some.config.option", "some-value") \
    .getOrCreate()

# sqlContext=HiveContext(spark)


#for 5 years data
#df = spark.read.parquet("s3n://csc591-dic-airline-data/super_reduced_dataset")

#for full dataset
df = spark.read.parquet("s3n://csc591-dic-airline-full/super_reduced_dataset_all")

df.createOrReplaceTempView("airline_tbl")


# model=RandomForestModel.load(spark, "target/tmp/myRandomForestRegressionModel")

model=RandomForestModel.load(spark, "s3n://csc591-dic-airline-full/randomforestmodel")
carries_list=pickle.load(open("carriers","rb"))
source_list=pickle.load(open("source","rb"))
destination_list=pickle.load(open("destination","rb"))


def json_converter_helper(df):
    list1 = df.toJSON().collect()
    json_string = ""
    count = 0
    for element in list1:
        json_string = json_string + str(element)
        count = count + 1
        if count < len(list1):
            json_string = json_string + ","
    return json.dumps(json_string).replace("\\", "")


def Delay_Statistics(start_date, end_date, carrier=None, origin_city=None, dest_city=None):
    sql_query = "SELECT SUM(CARRIER_DELAY) as carrer_delay,SUM(WEATHER_DELAY) as weather_delay,SUM(NAS_DELAY) as nas_delay,SUM(SECURITY_DELAY) as security_delay,SUM(LATE_AIRCRAFT_DELAY) as late_aircraft \
            FROM airline_tbl\
            WHERE FL_DATE >='" + start_date + "' AND FL_DATE<='" + end_date + "'\
            "
    if carrier != None and carrier != "":
        sql_query = sql_query + " AND UNIQUE_CARRIER = '" + carrier + "'";
    if origin_city != None and origin_city != "":
        sql_query = sql_query + " AND ORIGIN_CITY_NAME = '" + origin_city + "'";
    if dest_city != None and dest_city != "":
        sql_query = sql_query + " AND DEST_CITY_NAME = '" + dest_city + "'";
    return spark.sql(sql_query)


def MostDelaysByCarrier(start_date, end_date, origin_city=None, dest_city=None):
    sql_query = "SELECT CARRIER,AVG(ARR_DELAY_NEW) as ARR_DELAY_AVG , AVG(DEP_DELAY_NEW) AS DEP_DELAY_AVG \
            FROM airline_tbl\
            WHERE FL_DATE >='" + start_date + "' AND FL_DATE<='" + end_date + "'\
          "
    if origin_city != None and origin_city != "":
        sql_query = sql_query + " AND ORIGIN_CITY_NAME = '" + origin_city + "'";
    if dest_city != None and dest_city != "":
        sql_query = sql_query + " AND DEST_CITY_NAME = '" + dest_city + "'";
    sql_query = sql_query + "GROUP BY CARRIER"
    intermediate_df = spark.sql(sql_query)
    intermediate_df.registerTempTable("temp_aggregate_tbl")
    sql_query = "SELECT CARRIER, ARR_DELAY_AVG,DEP_DELAY_AVG \
                FROM temp_aggregate_tbl\
                ORDER BY ARR_DELAY_AVG desc\
                LIMIT 10";

    return spark.sql(sql_query)


def CarrierWithMaximumCancelledFlights(start_date, end_date, origin_city=None, dest_city=None):
    # returns carrier, cancelled_total, total

    sql_query = "SELECT CARRIER, SUM(CANCELLED) as CANCELLED_TOTAL,COUNT(1) AS TOTAL \
            FROM airline_tbl\
            WHERE FL_DATE >='" + start_date + "' AND FL_DATE<='" + end_date + "'\
          "
    if origin_city != None and origin_city != "":
        sql_query = sql_query + " AND ORIGIN_CITY_NAME = '" + origin_city + "'";
    if dest_city != None and dest_city != "":
        sql_query = sql_query + " AND DEST_CITY_NAME = '" + dest_city + "'";
    sql_query = sql_query + "GROUP BY CARRIER"
    intermediate_df = spark.sql(sql_query)
    intermediate_df.registerTempTable("temp_aggregate_tbl")
    sql_query = "SELECT CARRIER, CANCELLED_TOTAL,TOTAL \
                FROM temp_aggregate_tbl\
                ORDER BY CANCELLED_TOTAL desc\
                LIMIT 10";

    return spark.sql(sql_query)


def CarrierWithMaximumAirTime(start_date, end_date):
    sql_query = "SELECT CARRIER, Air_Time, FL_NUM , ORIGIN_CITY_NAME ,DEST_CITY_NAME \
            FROM airline_tbl\
            WHERE FL_DATE >='" + start_date + "' AND FL_DATE<='" + end_date + "'"
    sql_query = sql_query + "ORDER BY CAST(Air_Time AS INT) desc limit 10"
    return spark.sql(sql_query)


def MostDelaysByMonth(origin_city=None, dest_city=None):
    sql_query = "SELECT MONTH, AVG(ARR_DELAY_NEW) as ARR_DELAY_AVG , AVG(DEP_DELAY_NEW) AS DEP_DELAY_AVG \
            FROM airline_tbl"
    if origin_city != None and origin_city != "":
        sql_query = sql_query + " WHERE ORIGIN_CITY_NAME = '" + origin_city + "'";
    if dest_city != None and dest_city != "":
        sql_query = sql_query + " AND DEST_CITY_NAME = '" + dest_city + "'";
    sql_query = sql_query + " GROUP BY MONTH "

    return spark.sql(sql_query)

def delay_prediction(start_date, carrier, source, destination):
    # rdd=spark.paraellize([month,day_of_month,day_of_week,carrier,source,destination,1000])
    # prediction=model.predict(rdd)
    # return json.dumps([prediction.collect()])
   # return json.dumps([0])
    date_list=start_date.split("-")
    month=date_list[1]
    day_of_month=date_list[2]
    day_of_week=date(int(date_list[0]),int(date_list[1]), int(date_list[2])).weekday()
    carrier=carries_list[carrier]
    source=source_list[source]
    destination=destination_list[destination]
    rdd=[int(month),int(day_of_month), int(day_of_week),carrier,source,destination,1000]
    prediction=model.predict(rdd)
    return json.dumps([prediction])


def query_delay_statistics(start_date, end_date, carrier=None, origin_city=None, dest_city=None):
    df = Delay_Statistics(start_date, end_date, carrier, origin_city, dest_city)
    return json_converter_helper(df)


def query_most_delay_by_carriers(start_date, end_date, origin_city=None, dest_city=None):
    df = MostDelaysByCarrier(start_date, end_date, origin_city, dest_city)
    return json_converter_helper(df)


def query_carriers_with_max_CF(start_date, end_date, origin_city=None, dest_city=None):
    df = CarrierWithMaximumCancelledFlights(start_date, end_date, origin_city, dest_city)
    return json_converter_helper(df)


def query_carriers_with_max_airtime(start_date, end_date):
    df = CarrierWithMaximumAirTime(start_date, end_date)
    return json_converter_helper(df)


def query_most_delays_by_months(origin_city=None, dest_city=None):
    df = MostDelaysByMonth(origin_city, dest_city)
    return json_converter_helper(df)

#print delay_prediction("2015-12-4","DL","JFK","BOS")
