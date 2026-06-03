# Lesson 1: Establishing the Driver
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687", # This is the connection string for my Neo4j database
    auth=("neo4j", "TestingCourse123!")       # This is the Neo4j username and password for the local DBSM
)

driver.verify_connectivity()



# executes a Cypher query and returns the results
records, summary, keys = driver.execute_query( # use driver.execute_query(<insert_query>) when you want to query in python
    "RETURN COUNT {()} AS count" # runs a Cypher query to get the count of all nodes in the database
)

# Get the first record
first = records[0]      # records contains a list of the rows returned, where the rows are a dict, so we take the only
                        # row that was returned so we can then access it like a dict in the next line

# Print the count entry
print(first["count"])   # the key to the dict was "count" and the valye is 169

#driver.close()          # shuts down connection from python to Neo4j, allows clean release of resources



# can instead use 'with' statement to create an all-in-one solution that automatically closes driver when block is exited
#with GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "TestingCourse123!")) as driver:
    #result, summary, keys = driver.execute_query("RETURN COUNT {()} AS count")


#--------------------------------------------------------------------------------------------
# Lesson 2: Executing Cypher Statements (preferred to use paramters in queries)
cypher = """
MATCH (p:Person {name: $name})-[r:ACTED_IN]->(m:Movie)
RETURN m.title AS title, r.roles AS role
""" # define the cypher statement

name = "Tom Hanks"

records, summary, keys = driver.execute_query( # returns tuple of records, summary, and keys
    cypher,    # first enter the cypher statement
    name=name  # Use the value of the Python variable name for the Cypher parameter $name.
)

#print(keys)
#print(records[0]["title"]) # because records is a list of dictionaries, you access the column you wish, then pass key

# Transforming results
result = driver.execute_query(
    cypher,
    name=name,
    # param allows you to automatically transform returned records b4 var assignment
    result_transformer_= lambda result: [   # result stores the raw list of records returned from query
        f"Tom Hanks played {record['role']} in {record['title']}"   # returns this for each record in the list
        for record in result
    ]
)

#print(result)  # ['Tom Hanks played Woody in Toy Story', ...]


# Working with DataFrames; transform the result into a pandas DataFrame
from neo4j import Result

driver.execute_query(
    cypher,
    name=name,
    result_transformer_=Result.to_df
)


# Reading vs. Writing
from neo4j import RoutingControl

driver.execute_query(
    cypher,
    name=name,
    result_transformer_=Result.to_df,
    routing_=RoutingControl.READ  # or simply "r" for read or "w" for write. by default, executre_query runs in write mode
)

#------------------------------------------------------------------------------------
# Lesson 3: Handling results, specifically Graph types which are returned in 3 types: Node, Relationship, Path
# Graph types: finds all movies with the specified title and returns person, acted_in and movie
movie = "Top Gun"

records, summary, keys = driver.execute_query("""
MATCH path = (person:Person)-[actedIn:ACTED_IN]->(movie:Movie {title: $title})
RETURN path, person, actedIn, movie
""", title=movie)

# Nodes are returned as a Node object
#print(records)
for record in records:
    node = record["movie"]
    print(node.element_id)      # ex: 4:97b72e9c-ae4d-427c-96ff-8858ecf16f88:
    print(node.labels)          # contains an array of labels attributed to the Node, ex: ['Person', 'Actor']
    print(node.items())         # provides access to the node's properties as a name-value pair, ex: {name: 'Tom Hanks', tmdbId: '31'}

    # single property can be retrieved by either using [] brackets or using the get() method
    print(node["name"])
    print(node.get("name", "N/A")) # N/A is the default property, will returned if property I'm trying to access doesn't exist on node

# Relationships are returned as a Relationship object
for record in records:
    acted_in = record["actedIn"]

    print(acted_in.id)         # Internal ID of the relationship (eg. 9876)
    print(acted_in.type)       # Type of relationship (eg. ACTED_IN)
    print(acted_in.items())    # Returns relationship properties as name-value pairs (eg. {role: 'Woody'})

    # Access properties using brackets [] or get() method
    print(acted_in["roles"])
    print(acted_in.get("roles", "(Unknown)"))

    print(acted_in.start_node) # Node object at the start of the relationship
    print(acted_in.end_node)   # Node object at the end of the relationship

# Paths are a sequence of nodes and relationships; returned as a Path object
for record in records:
    path = record["path"]

    print(path.start_node)  # Node object at the start of the path
    print(path.end_node)    # Node object at the end of the path
    print(len(path))  # The number of relationships within the path
    print(path.relationships)  # An tuple of Relationship objects within the path.
# NOTE: paths are itterable, can use iter(path) to iterate over the relationships in a path

#------------------------------------------------------------------------------------------------------
# Lesson 4: Dates and times; looking at temporal types in Neo4j, which are combos of date, time, and timezone elements
from neo4j.time import DateTime
from datetime import timezone, timedelta


driver.execute_query("""
CREATE (e:Event {
  startsAt: $datetime,              // Use a DateTime object as a parameter to the query (<4>)
  createdAt: datetime($dtstring),   // casting a string within a Cypher statement
  updatedAt: datetime()             // Get the current date and time using the datetime() function.
})
""",
    datetime=DateTime(
        2024, 5, 15, 14, 30, 0,
        tzinfo=timezone(timedelta(hours=2))
    ),  # (<4>)
    dtstring="2024-05-15T14:30:00+02:00"
)

# Reading temporal types
# When reading temporal types from DB, you receive an instance of the corresponding Python type
# unless you cast the value within your query

# Query returning temporal types
records, summary, keys = driver.execute_query("""
RETURN date() as date, time() as time, datetime() as datetime, toString(datetime()) as asString
""")

# Access the first record
for record in records:
    # Automatic conversion to Python driver types
    date = record["date"]           # neo4j.time.Date
    time = record["time"]           # neo4j.time.Time
    datetime = record["datetime"]   # neo4j.time.DateTime
    as_string = record["asString"]  # str


# Working with Durations
from neo4j.time import Duration, DateTime

starts_at = DateTime.now()
event_length = Duration(hours=1, minutes=30)
ends_at = starts_at + event_length

driver.execute_query("""
CREATE (e:Event {
  startsAt: $startsAt, endsAt: $endsAt,
  duration: $eventLength, // Pass an instance of Duration to the query
  interval: duration('P30M') // Use the duration() function to create a Duration object from a string
})
""",
    startsAt=starts_at, endsAt=ends_at, eventLength=event_length
) # NOTE: can use duration.between method to calculate the duration between two date or time objects

#--------------------------------------------------------------------------------------------------
# Lesson 5: Spatial types
# Creating a 2D or 3D cartesian point
from neo4j.spatial import CartesianPoint
"""
two_d = CartesianPoint((x, y))
three_d = CartesianPoint((x, y, z))
"""

# the driver converts point data types created with x, y, z values to an instance of CartesianPoint class
records, summary, keys = driver.execute_query("""
RETURN point({x: 1.23, y: 4.56, z: 7.89}) AS threeD
""")

point = records[0]["threeD"]

# <1> Accessing attributes
print(point.x, point.y, point.z, point.srid) # 1.23, 4.56, 7.89, 9157

# <2> Destructuring
x, y, z = point


# Working with WGS84Point (World Geodetic System) point consists of a latitude and longitude value)
# An additional height value can be provided to define a 3D point
from neo4j.spatial import WGS84Point

ldn = WGS84Point((-0.118092, 51.509865))
print(ldn.longitude, ldn.latitude, ldn.srid) # -0.118092, 51.509865, 4326; NOTE: always must be in this order

shard = WGS84Point((-0.086500, 51.504501, 310))
print(shard.longitude, shard.latitude, shard.height, shard.srid) # -0.0865, 51.504501, 310, 4979

# Using destructuring
longitude, latitude, height = shard

# driver will return WGS84Point objects when point data types are created with latitude and longitude values in Cypher
# values can be accessed using the longitude, latitude and height attributes or by destructuring the point
records, summary, keys = driver.execute_query("""
RETURN point({
    latitude: 51.5,
    longitude: -0.118,
    height: 100
}) AS point
""")

point = records[0]["point"]
longitude, latitude, height = point


# point.distance function can be used to calculate the distance between two points with the same point type (cartesian or WGS84)
# Create two points
point1 = CartesianPoint((1, 1))
point2 = CartesianPoint((10, 10))

# Query the distance using Cypher
records, summary, keys = driver.execute_query("""
RETURN point.distance($p1, $p2) AS distance
""", p1=point1, p2=point2)

# Print the distance from the result
distance = records[0]["distance"]
print(distance)  # 12.727922061357855

#----------------------------------------------------------------------------------------------------
# Lesson 6: Transaction Management
# Drawback of execute_query() is that the record is only available once the entire final result is returned
# Therefore, long running queries it can lead to a long wait for results

# ALSO, Neo4j is an ACID-compliant transactional DB, meaning queries are executed as part of a single atomic transaction

# To execute transactions, must open session:
with driver.session() as session:
    # Call transaction functions here
    # Because we started by a 'with', it will automatically close the session once the block is exited
    pass

# session object provides two methods for managing transactions:
    # Session.execute_read()
    # Session.execute_write()

# functions will retry if transient errors (network issue) occurs automatically


# Unit of Work patterns: (unit of work = pattern that groups related operations into a single transaction)
def create_person(tx, name, age): # 1st arg is always a ManagedTransaction object, which is provided when you call
                                  #  execute_read() or _write()
    result = tx.run("""
    CREATE (p:Person {name: $name, age: $age})
    RETURN p
    """, name=name, age=age) # The run() method on the ManagedTransaction object is called to execute a Cypher statement

# can execute multiple queries within the same transaction function to ensure all operations completed or failed as a unit
def transfer_funds(tx, from_account, to_account, amount):
    # Deduct from first account
    tx.run(
        "MATCH (a:Account {id: $from_}) SET a.balance = a.balance - $amount",
        from_=from_account, amount=amount
    )

    # Add to second account
    tx.run(
        "MATCH (a:Account {id: $to}) SET a.balance = a.balance + $amount",
        to=to_account, amount=amount
    )


# Handling outputs:
with driver.session() as session:
    def get_answer(tx, answer):
        result = tx.run("RETURN $answer AS answer", answer=answer)

        return result.consume()

    # Call the transaction function
    summary = session.execute_read(get_answer, answer=42)

    # Output the summary
    print(
        "Results available after", summary.result_available_after,
        "ms and consumed after", summary.result_consumed_after, "ms"
    )

#-------------------------------------------------------------------------------------------
# Lesson 7: Handling Database Errors
# CypherSyntaxError - Raised when the Cypher syntax is invalid
# ConstraintError - Raised when a constraint unique or other is violated
# AuthError - Raised when authentication fails
# TransientError - Raised when the database is not accessible