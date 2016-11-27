
import sys
import os
import json
os.environ['SPARK_HOME'] = "/usr/lib/spark"
sys.path.append("/usr/lib/spark/python")
sys.path.append("/usr/lib/spark/python/lib/py4j-0.10.3-src.zip")

try:
    from pyspark import SparkContext
    from pyspark import SparkConf
    from pyspark.sql import HiveContext
    from pyspark.sql import SparkSession
    from pyspark.sql.types import *
except ImportError as e:
    print ("error importing spark modules", e)
    sys.exit(1)

spark = SparkSession.builder \
    .appName("DIC FINAL PROJECT") \
    .enableHiveSupport() \
    .config("spark.some.config.option", "some-value") \
    .getOrCreate()


#sqlContext=HiveContext(spark)


df = spark.read.parquet("s3n://csc591-dic-airline-data/reduced_dataset")
df.createOrReplaceTempView("airline_tbl")



def json_converter_helper(df):
    list1=df.toJSON().collect()
    list2=[]
    for element in list1:
        list2.append(str(element))
    return json.dumps(list2)

def Delay_Statistics(start_year, end_year, start_month, end_month, airline_id=None, origin_city=None, dest_city=None):
    # returns (Arrival_delay,departure_delay,career_delay,weather_delay,nas_delay,sec_delay,late_aircraft_delay)
    start_date = start_year + "-" + start_month + "-01"
    end_date = end_year + "-" + end_month + "-31"
    sql_query = "SELECT SUM(CARRIER_DELAY) as carrier_delay,SUM(WEATHER_DELAY) as weather_delay,SUM(NAS_DELAY) as nas_delay,SUM(SECURITY_DELAY) as sec_delay ,SUM(LATE_AIRCRAFT_DELAY) as late_aircraft_delay \
            FROM airline_tbl\
            WHERE FL_DATE >='" + start_date + "' AND FL_DATE<='" + end_date + "'\
            "
    if airline_id != None and airline_id != "":
        sql_query = sql_query + "AND AIRLINE_ID = '" + airline_id + "'"
    if origin_city != None and origin_city != "":
        sql_query = sql_query + "AND ORIGIN_CITY_NAME = '" + origin_city + "'"
    if dest_city != None and dest_city != "":
        sql_query = sql_query + "AND DEST_CITY_NAME = '" + dest_city + "'"
    return spark.sql(sql_query)

def query_delay_statistics(start_year, end_year, start_month, end_month, airline_id=None, origin_city=None, dest_city=None):
    df=Delay_Statistics(start_year, end_year, start_month, end_month, airline_id, origin_city, dest_city)
    return json_converter_helper(df)

def MostDelaysByCarrier(start_year,end_year,start_month,end_month,origin_city = None,dest_city = None):
    start_date =  start_year + "-" + start_month + "-01"
    end_date = end_year+"-" + end_month + "-31"
    sql_query =  "SELECT CARRIER,AVG(ARR_DELAY_NEW) as ARR_DELAY_AVG , AVG(DEP_DELAY_NEW) AS DEP_DELAY_AVG \
            FROM airline_tbl\
            WHERE FL_DATE >='"+start_date +"' AND FL_DATE<='" + end_date + "'\
          "
    if origin_city !=None and origin_city !="":
        sql_query = sql_query + " AND ORIGIN_CITY_NAME = '" + origin_city + "'";
    if dest_city !=None and dest_city !="":
        sql_query = sql_query + " AND DEST_CITY_NAME = '" + dest_city + "'";
    sql_query = sql_query + "GROUP BY CARRIER"
    intermediate_df = spark.sql(sql_query) 
    intermediate_df.registerTempTable("temp_aggregate_tbl")    
    sql_query = "SELECT CARRIER, ARR_DELAY_AVG,DEP_DELAY_AVG \
                FROM temp_aggregate_tbl\
                ORDER BY ARR_DELAY_AVG desc\
                LIMIT 10";
        
    return spark.sql(sql_query)    


def CarrierWithMaximumCancelledFlights(start_year,end_year,start_month,end_month,origin_city = None,dest_city = None):
    #returns carrier, cancelled_total, total
    start_date =  start_year + "-" + start_month + "-01"
    end_date = end_year+"-" + end_month + "-31"
    sql_query =  "SELECT CARRIER, SUM(CANCELLED) as CANCELLED_TOTAL,COUNT(1) AS TOTAL \
            FROM airline_tbl\
            WHERE FL_DATE >='"+start_date +"' AND FL_DATE<='" + end_date + "'\
          "
    if origin_city !=None and origin_city !="":
        sql_query = sql_query + " AND ORIGIN_CITY_NAME = '" + origin_city + "'";
    if dest_city !=None and dest_city !="":
        sql_query = sql_query + " AND DEST_CITY_NAME = '" + dest_city + "'";
    sql_query = sql_query + "GROUP BY CARRIER"
    intermediate_df = spark.sql(sql_query) 
    intermediate_df.registerTempTable("temp_aggregate_tbl")    
    sql_query = "SELECT CARRIER, CANCELLED_TOTAL,TOTAL \
                FROM temp_aggregate_tbl\
                ORDER BY CANCELLED_TOTAL desc\
                LIMIT 10";   
    
    return spark.sql(sql_query)      

def CarrierWithMaximumAirTime(start_year,end_year,start_month,end_month):
    start_date =  start_year + "-" + start_month + "-01"
    end_date = end_year+"-" + end_month + "-31"
    sql_query =  "SELECT CARRIER, Air_Time, FL_NUM , ORIGIN_CITY_NAME ,DEST_CITY_NAME \
            FROM airline_tbl\
            WHERE FL_DATE >='"+start_date +"' AND FL_DATE<='" + end_date + "'"
    sql_query = sql_query + "ORDER BY Air_Time desc limit 10"
    return spark.sql(sql_query)

def query_most_delay_by_carriers(start_year,end_year,start_month,end_month,origin_city = None,dest_city = None):
    
    df=MostDelaysByCarrier(start_year,end_year,start_month,end_month,origin_city = None,dest_city = None)
    return json_converter_helper(df)

def query_carriers_with_max_CF(start_year,end_year,start_month,end_month,origin_city = None,dest_city = None):

    df=CarrierWithMaximumCancelledFlights(start_year,end_year,start_month,end_month,origin_city = None,dest_city = None)
    return json_converter_helper(df)

def query_carriers_with_max_airtime(start_year,end_year,start_month,end_month):

    df=CarrierWithMaximumAirTime(start_year,end_year,start_month,end_month)
    return json_converter_helper(df)

    

