#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: shreyamacherla
"""

import pandas as pd;
import seaborn as sns;
import numpy as np;
from matplotlib import pyplot as plt
from pandasql import sqldf
pysqldf = lambda q: sqldf(q, globals())
from mlxtend.frequent_patterns import apriori
from mlxtend.preprocessing import TransactionEncoder 
from mlxtend.frequent_patterns import association_rules
import networkx as nx


data=pd.read_excel("OnlineRetail.xlsx")
print(data.columns)
print(data.describe())
print(data.shape)

# Convert to proper format
data.dropna(axis = 0, subset = ['InvoiceNo'], inplace = True)
data['InvoiceNo'] = data['InvoiceNo'].astype('str')
data['InvoiceDate'] = pd.to_datetime(data['InvoiceDate'])
data['Amount'] = data.Quantity * data.UnitPrice
data.CustomerID = data.CustomerID.astype('Int64')

print(data.head())

# Data Preprocessing

# Removing low variance columns from data as they don't account for much insights.
data.std() == 0
data=data.drop(data.std()[data.std()==0].index,axis=1)#removing numerical zero variance
categorical_var=list(data.dtypes[data.dtypes == object].index)
zero_cardinality = [] 

# Based on the cardinality, figure out the columns with zero variance and filter them out.
for category in categorical_var: 
    if len(data[category].value_counts().index) == 1: 
        zero_cardinality.append(category) 
        
# Drop zero variance columns.
data = data.drop(zero_cardinality,axis=1) 

# Check missing values
data_missing = data.isna().sum()
pers_missing = data_missing * 100 / len(data)
print(pers_missing)
        
# Unit price and quantity values are negative for some items
# Checking accounts with negative and zero unit price
print(len(data[data['UnitPrice'] <= 0]))
data = data[~(data['UnitPrice'] <= 0)]
# Checking accounts with negative quantity
print(len(data[data['Quantity']<0]))
data=data[~(data['Quantity']<0)]

data[data['CustomerID'].isnull()]
data=data[~(data['CustomerID'].isnull())]

data_missing=data.isna().sum()
print(data_missing)

# Check rows with same stock code but different descripitions
data_descrip = data.groupby(['StockCode','Description']).count().reset_index()
# For these column item same but description entered different due to manual error
print(data[data['StockCode'] == data_descrip.StockCode.value_counts()[data_descrip.StockCode.value_counts()>1].reset_index()['index'][211]]['Description'].unique()) #change '2' to display more erroneous results
# Remove the above inconsitency
uniq_desc_tbl=data[['StockCode','Description']].groupby(['StockCode']).apply(pd.DataFrame.mode).reset_index(drop=True)
print(uniq_desc_tbl)
query = ''' select d.InvoiceNo, d.StockCode, d.Amount, u.Description, d.Quantity,d.InvoiceDate,d.UnitPrice,d.CustomerID,d.Country from data as d
 INNER JOIN uniq_desc_tbl as u ON d.StockCode=u.StockCode'''
final_data=pysqldf(query)
final_data.columns

# Removing Spaces from description
final_data['Description']=final_data['Description'].str.strip()
final_data['Country']=final_data['Country'].str.strip()
final_data['Country'] = final_data['Country'].astype('category')
final_data['InvoiceNo']=final_data['InvoiceNo'].astype('str')
final_data=final_data[~final_data['InvoiceNo'].str.contains('C')]

print(final_data.shape)


# Association Rule Mining
# Mine Rules for top 3 countries
top3=final_data.groupby(['Country']).count()
print(top3.nlargest(3,'InvoiceNo'))

# Encoding to 0/1 bit and dropping unnecessary columns
def encode_units(x):
     if x <= 0:
         return 0
     if x >= 1:
         return 1

# Derive insights for frequently brought items based on the metric thresholds.
def derive_insights(country, minSupport, minConfidence, minLift): 
    basket = (final_data[final_data['Country'] == country]
               .groupby(['InvoiceNo', 'Description'])['Quantity']
               .sum().unstack().reset_index().fillna(0)
               .set_index('InvoiceNo'))
    
    print(basket.head())
    print(basket.shape)
    
    baskets=basket.applymap(encode_units)
    baskets.drop('POSTAGE',inplace=True,axis=1)
    
    #Applying Apriori algorithm and filtering out rules on the basis of support,confidence,lift
    frequent_items=apriori(baskets,min_support=minSupport,use_colnames=True)
    print(frequent_items.sort_values(['support'], ascending=False).head())
    
    rules=association_rules(frequent_items,metric="lift",min_threshold=1)

    rules = rules[(rules['confidence'] > minConfidence) & (rules['lift'] > minLift)]
    
    # Get top 5 rules
    rules_tran=pd.DataFrame(rules[['antecedents','consequents','lift','confidence','support']])
    
    #filter top rules
    top_rules=rules_tran.groupby(['antecedents', 'consequents']).first().reset_index().sort_values(['support', 'confidence', 'lift'],ascending=False).head()
    print(top_rules)
    
    # Support vs Confidence plot
    plt.figure(figsize=(10,10))
    g=sns.stripplot(round(rules_tran['support'],2), round(rules_tran['confidence'],2),data=rules_tran,jitter=True)
    plt.title(' Support vs Confidence plot for '+country,size=30)
    plt.show()
    draw_rules(top_rules,country)
    return top_rules


# Showing Associations among top 5 items bought together.
def draw_rules(rules,country):
    plt.figure(figsize=(15,10))
    Graph=nx.DiGraph()
    node_color=[]
    rule_no=['R0','R1','R2','R3','R4']
    for i in range(len(rule_no)):
        Graph.add_nodes_from([rule_no[i]])
        for a in rules.iloc[i]['antecedents']:
            Graph.add_nodes_from([a])
            Graph.add_edge(a, rule_no[i])
        for c in rules.iloc[i]['consequents']:
            Graph.add_nodes_from([c])
            Graph.add_edge(rule_no[i], c)
    edges=Graph.edges()
    for node in Graph:
        flag_rule=0;
        for i in rule_no:
            if i==node:
                flag_rule=1
        if flag_rule==1:
            node_color.append('red')
        else:
            node_color.append('green')
    pos=nx.planar_layout(Graph)
    nx.draw(Graph,pos)
    for i in pos: 
            pos[i][1] += 0.03
    nx.draw_networkx_labels(Graph,pos)
    plt.title('Top 5 Associations for '+country,size=30)
    plt.show()

top_rules_uk =  derive_insights("United Kingdom", 0.02, 0.6, 7)

top_rules_ger = derive_insights("Germany", 0.04, 0.5, 2)

top_rules_fr = derive_insights("France", 0.1, 0.7, 4)

















































