

#Importing libraries

import pandas as pd
import os
get_ipython().run_line_magic('matplotlib', 'inline')

import numpy as np 
import matplotlib.pyplot as plt 
import seaborn as sns


# Reading data file
df=pd.read_csv("hotel_bookings.csv")
df.head()

# Defining shape
print("Shape: ", df.shape)


# Checking for null values
print("Nulls in raw data: ")
print(df.isnull().sum())

# Cleaning up null values
def clean_fun(df):
    df.fillna(0,inplace=True)
    print(df.isnull().sum())
    
print("Nulls after cleanup of data: ")
clean_fun(df)

# Displaying columns
print("Columns: ", df.columns)


list=['adults', 'children', 'babies']
for person in list:
    print("{} has unique value as {}".format(person,df[person].unique()))
    


# In[23]:


filter=(df["adults"]==0) & (df["children"]==0) & (df["babies"]==0)


# In[24]:


df[filter]


# In[25]:


pd.set_option("display.max_column",32)


# In[26]:


filter=(df["adults"]==0) & (df["children"]==0) & (df["babies"]==0)
df[filter].head()


# In[27]:


data=df[~filter]


# In[28]:


data.shape


# In[29]:


country_wise_data=data[data['is_canceled']==0]["country"].value_counts().reset_index()


# In[30]:


country_wise_data.columns=["country","no of guest"]


# In[31]:


country_wise_data.columns


# In[32]:


import folium
from folium.plugins import HeatMap
basemap=folium.Map()
import plotly.express as px
import plotly.io as pio
pio.renderers.default='notebook'


# In[33]:


map_guest=px.choropleth(country_wise_data,
                        locations=country_wise_data["country"],
                        color=country_wise_data["no of guest"],
                        hover_name=country_wise_data["country"],
                        title="home country of guest")
map_guest.show()


# In[59]:


#how mch do guest pay for the room per night


# In[34]:


data2=data[data['is_canceled']==0]


# In[35]:


data2.columns


# In[36]:


data2[["adr","reserved_room_type"]]


# In[38]:


plt.figure(figsize=(9,8))
sns.boxplot(x="reserved_room_type",y="adr",hue="hotel",data=data2)
plt.title("Room price per night according to person")
plt.xlabel("Type - Room")
plt.ylabel("Euro - Price")
plt.legend()
plt.show()


# how does th pricee pr night vary over the year

# In[39]:


data_resort=data[(data['hotel']=='Resort Hotel') & (data["is_canceled"]==0)]
data_city=data[(data['hotel']=='City Hotel') & (data["is_canceled"]==0)]


# In[40]:


data_resort.head()


# In[43]:


resort_hotel=data_resort.groupby(["arrival_date_month"])["adr"].mean().reset_index()


# In[44]:


city_hotel=data_city.groupby(["arrival_date_month"])["adr"].mean().reset_index()


# In[45]:


final=resort_hotel.merge(city_hotel,on ="arrival_date_month")


# In[46]:


final.columns=["month","price of resort","price of city"]


# In[47]:


import sort_dataframeby_monthorweek as sd


# In[48]:


def sort_data(df,columns):
    return sd.Sort_Dataframeby_Month(df,columns)


# In[50]:


final=sort_data(final,"month")


# In[54]:


px.line(final,x="month",y=["price of resort","price of city"],title="room pricee peer night over the month")


# no of guest over the month
# 

# In[55]:


rush_resort=data_resort["arrival_date_month"].value_counts().reset_index()
rush_resort.columns=["month","no of guest"]
rush_resort


# In[56]:


rush_city=data_city["arrival_date_month"].value_counts().reset_index()
rush_city.columns=["month","no of guest"]
rush_city


# In[57]:


final_rush=rush_resort.merge(rush_city,on="month")


# In[58]:


final_rush.columns=["month","no of guest in resort","no of guest in city"]


# In[59]:


final_rush


# In[60]:


def sort_rush(df,columns):
    return sd.Sort_Dataframeby_Month(df,columns)


# In[62]:


final_rush=sort_rush(final_rush,"month")


# In[68]:


px.line(final_rush,x="month",y=["no of guest in resort","no of guest in city"],title="no of guest over the month")


# In[69]:


co_relation=data.corr()
co_relation["is_canceled"]


# In[70]:


co_relation["is_canceled"].abs().sort_values(ascending=False)


# In[71]:


data.groupby("is_canceled")["reservation_status"].value_counts()


# In[72]:


list_not=["days_in_waiting_list",'arrival_date_year']


# In[73]:


cols=[]
for col in data.columns:
    if data[col].dtype!="O" and col not in list_not:
        cols.append(col)


# In[74]:


cols


# In[75]:


num_feature=[col for col in data.columns if data[col].dtype!="O" and col not in list_not]


# In[76]:


data.columns


# In[77]:


cat_not=["arrival_date_year","assigned_room_type","booking_changes","reservation_status","country","days_in_waiting_list"]


# In[78]:


cat_featuree=[col for col in data.columns if data[col].dtype=="O" and col not in cat_not]


# In[79]:


data_cat=data[cat_featuree]


# In[80]:


data_cat


# In[81]:


data_cat.info()


# In[82]:


import warnings
from warnings import filterwarnings
filterwarnings("ignore")


# In[83]:


data_cat["reservation_status_date"]=pd.to_datetime(data["reservation_status_date"])


# In[84]:


data_cat["year"]=data_cat["reservation_status_date"].dt.year
data_cat["month"]=data_cat["reservation_status_date"].dt.month
data_cat["day"]=data_cat["reservation_status_date"].dt.day


# In[85]:


data_cat.head()


# In[86]:


data_cat.drop("reservation_status_date",axis=1,inplace=True)


# In[87]:


data.dtypes


# In[88]:


data_cat["cancellation"]=data["is_canceled"]


# In[89]:


data_cat.head()


# In[90]:


#feature encoding (mean endong)


# In[91]:


cols=data_cat.columns[0:8]


# In[92]:


cols


# In[93]:


for col in cols:
    dict=data_cat.groupby(col)["cancellation"].mean().to_dict()
    data_cat[col]=data_cat[col].map(dict)


# In[94]:


data_cat.head()


# In[95]:


dataframe=pd.concat([data_cat,data[num_feature]],axis=1)


# In[96]:


dataframe.head()


# In[97]:


dataframe.drop("cancellation",axis=1,inplace=True)


# In[98]:


dataframe


# ### outlier detaection

# In[99]:


sns.distplot(dataframe["lead_time"])


# In[100]:


def handle_oulier(col):
    dataframe[col]=np.log1p(dataframe[col])
    


# In[101]:


handle_oulier("lead_time")


# In[102]:


sns.distplot(dataframe["lead_time"])


# In[86]:


sns.distplot(dataframe["adr"])


# In[87]:


handle_oulier("adr")


# In[88]:


sns.distplot(dataframe["adr"].dropna())


# In[106]:


#most imp feature


# In[108]:


y=dataframe['is_canceled']
x=dataframe.drop("is_canceled",axis=1)


# In[ ]:




