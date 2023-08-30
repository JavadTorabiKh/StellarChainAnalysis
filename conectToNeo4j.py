from neo4j import GraphDatabase
import json

# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "123456789")



def getRecords(p1 , p2):
    with GraphDatabase.driver(URI, auth=AUTH) as driver: 
        driver.verify_connectivity()
    records, summary, keys = driver.execute_query(
        'MATCH ('+p1+':NODE {name:"'+p1+'"}),('+p2+':NODE {name:"'+p2+'"}), p = shortestPath(('+p1+')-[*]->('+p2+')) RETURN p  as name',
        database_="neo4j",
    )
    driver.close()
    return records

 
def getData(p1,p2):
    account = []
    amount = [] 
    records = getRecords(p1,p2)
    for record in records:  
        for i in record["name"]:
            a1=str(i)[188:244]
            a2=str(i)[359:415]
            a3=str(i)[457:471]
            amount.append(a3)
            
            if a1 not in account:
                account.append(a1)
            if a2 not in account:
                account.append(a2)
    return account, amount


# ("GD3ZN2T6QQMKLAGKKMWHHU4FITANVJBTREEJERHTWGWF2GSBPOSHGCLU","GBT67MMDODT5NTYWQGDUFEQGMF2MQT5JHOUFYHVXOIB4PL3QSOPRNAHO")        
# print(account)
# print(amount)
