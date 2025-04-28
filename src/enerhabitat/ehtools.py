import pandas as pd
import numpy as np
import warnings
import math
from dateutil.parser import parse

"""
=============================
        Herramientas
=============================
"""

def temperature_model(df, Tmin, Tmax, Ho, Hi):
    """
    Calcula la temperatura ambiente y agrega una columna 'Ta' al DataFrame.

    Parameters:
        df (pd.DataFrame): DataFrame con la columna 'index' que representa los tiempos.
        Tmin (float): Temperatura mínima.
        Tmax (float): Temperatura máxima.
        Ho (float): Hora de amanecer (en horas).
        Hi (float): Hora de m'axima temperatura (en horas).

    Returns:
        pd.DataFrame: DataFrame con una nueva columna 'Ta' que contiene la temperatura ambiente.
    """
    Ho_sec = Ho * 3600
    Hi_sec = Hi * 3600
    day_hours = 24 * 3600
    times = pd.to_datetime(df.index)
    y = np.zeros(len(times))
    
    for i, t in enumerate(times):
        t_sec = t.hour * 3600 + t.minute * 60 + t.second
        if t_sec <= Ho_sec:
            y[i] = (math.cos(math.pi * (Ho_sec - t_sec) / (day_hours + Ho_sec - Hi_sec)) + 1) / 2
        elif Ho_sec < t_sec <= Hi_sec:
            y[i] = (math.cos(math.pi * (t_sec - Ho_sec) / (Hi_sec - Ho_sec)) + 1) / 2
        else:
            y[i] = (math.cos(math.pi * (day_hours + Ho_sec - t_sec) / (day_hours + Ho_sec - Hi_sec)) + 1) / 2

    Ta = Tmin + (Tmax - Tmin) * (1 - y)
    df['Ta'] = Ta
    return df

def calculate_tTmaxTminTmax(mes,epw):
    # epw = read_epw(f_epw,alias=True,year='2024')
    epw_mes = epw.loc[epw.index.month==int(mes)]
    hora_minutos = epw_mes.resample('D').To.idxmax()
    hora = hora_minutos.dt.hour
    minuto = hora_minutos.dt.minute
    tTmax = hora.mean() +  minuto.mean()/60 
    # epw_mes = epw.loc[epw.index.month==int(mes)]
    # horas  = epw_mes.resample('D').To.idxmax().resample('ME').mean().dt.hour 
    # minutos = epw_mes.resample('D').To.idxmax().resample('ME').mean().dt.minute
    # tTmax = horas.iloc[0]+ minutos.iloc[0]/60 
    Tmin =  epw_mes.resample('D').To.min().resample('ME').mean().iloc[0]
    Tmax =  epw_mes.resample('D').To.max().resample('ME').mean().iloc[0]
    
    return tTmax,Tmin,Tmax

def add_IgIbId_Tn(dia,epw,mes,f1,f2,timezone):
    # epw = read_epw(f_epw,alias=True,year='2024')
    epw_mes = epw.loc[epw.index.month==int(mes)]
    Irr = epw_mes.groupby(by=epw_mes.index.hour)[['Ig','Id','Ib']].mean()
    tiempo = pd.date_range(start=f1, end=parse(f2), freq='1h',tz=timezone)
    Irr.index = tiempo
    Irr = Irr.resample('1s').interpolate(method='time')
    dia['Ig'] = Irr.Ig
    dia['Ib'] = Irr.Ib
    dia['Id'] = Irr.Id
    dia.ffill(inplace=True)
    dia['Tn'] = 13.5 + 0.54*dia.Ta.mean()
    
    return dia

def calculate_DtaTn(Delta):
    if Delta < 13:
        tmp2 = 2.5 / 2
    elif 13 <= Delta < 16:
        tmp2 = 3.0 / 2
    elif 16 <= Delta < 19:
        tmp2 = 3.5 / 2
    elif 19 <= Delta < 24:
        tmp2 = 4.0 / 2
    elif 24 <= Delta < 28:
        tmp2 = 4.5 / 2
    elif 28 <= Delta < 33:
        tmp2 = 5.0 / 2
    elif 33 <= Delta < 38:
        tmp2 = 5.5 / 2
    elif 38 <= Delta < 45:
        tmp2 = 6.0 / 2
    elif 45 <= Delta < 52:
        tmp2 = 6.5 / 2
    elif Delta >= 52:
        tmp2 = 7.0 / 2
    else:
        tmp2 = 0  # Opcional, para cubrir cualquier caso no contemplado, aunque el rango anterior es exhaustivo

    return tmp2

def get_sunrise_sunset_times(df):
#   Función para calcular Ho y Hi
    sunrise_time = df[df['elevation'] >= 0].index[0]
    sunset_time = df[df['elevation'] >= 0].index[-1]
    
    Ho = sunrise_time.hour + sunrise_time.minute / 60
    Hi = sunset_time.hour + sunset_time.minute / 60
    
    return Ho, Hi

def readEPW(file,year=None,alias=False,warns=True):
    """
    Read EPW file 

    Args:
        file : path location of EPW file
        year : None default to leave intact the year or change if desired. It raises a warning.
        alias : False default, True to change to To, Ig, Ib, Ws, RH, ...
    
    Return:
        tuple: 
            epw - DataFrame
            latitud - float
            longitud - float
            altitud - float
            timezone - int
    """
    
    datos=[]
    with open(file,'r') as epw:
        datos=epw.readline().split(',')
    lat = float(datos[6])
    lon = float(datos[7])
    alt = float(datos[9])
    tmz = int(datos[8].split('.')[0])
    
    names = ['Year',
             'Month',
             'Day',
             'Hour',
             'Minute',
             'Data Source and Uncertainty Flags',
             'Dry Bulb Temperature',
             'Dew Point Temperature',
             'Relative Humidity',
             'Atmospheric Station Pressure',
             'Extraterrestrial Horizontal Radiation',
             'Extraterrestrial Direct Normal Radiation',
             'Horizontal Infrared Radiation Intensity',
             'Global Horizontal Radiation',
             'Direct Normal Radiation',
             'Diffuse Horizontal Radiation',
             'Global Horizontal Illuminance',
             'Direct Normal Illuminance',
             'Diffuse Horizontal Illuminance',
             'Zenith Luminance',
             'Wind Direction',
             'Wind Speed',
             'Total Sky Cover',
             'Opaque Sky Cover',
             'Visibility',
             'Ceiling Height',
             'Present Weather Observation',
             'Present Weather Codes',
             'Precipitable Water',
             'Aerosol Optical Depth',
             'Snow Depth',
             'Days Since Last Snowfall',
             'Albedo',
             'Liquid Precipitation Depth',
             'Liquid Precipitation Quantity']
       
    rename = {'Dry Bulb Temperature'       :'To',
             'Relative Humidity'           :'RH',
             'Atmospheric Station Pressure':'P' ,
             'Global Horizontal Radiation' :'Ig',
             'Direct Normal Radiation'     :'Ib',
             'Diffuse Horizontal Radiation':'Id',
             'Wind Direction'              :'Wd',
             'Wind Speed'                  :'Ws'}
    
    data = pd.read_csv(file,skiprows=8,header=None,names=names,usecols=range(35))
    data.Hour = data.Hour -1
    if year != None:
        data.Year = year
        if warns == True:
            warnings.warn("Year has been changed, be carefull")
    try:
        data['tiempo'] = data.Year.astype('str') + '-' + data.Month.astype('str')  + '-' + data.Day.astype('str') + ' ' + data.Hour.astype('str') + ':' + data.Minute.astype('str') 
        data.tiempo = pd.to_datetime(data.tiempo,format='%Y-%m-%d %H:%M')
    except:
        data.Minute = 0
        data['tiempo'] = data.Year.astype('str') + '-' + data.Month.astype('str')  + '-' + data.Day.astype('str') + ' ' + data.Hour.astype('str') + ':' + data.Minute.astype('str') 
        data.tiempo = pd.to_datetime(data.tiempo,format='%Y-%m-%d %H:%M')

    data.set_index('tiempo',inplace=True)
    del data['Year']
    del data['Month']
    del data['Day']
    del data['Hour']
    del data['Minute']
    if alias:
        data.rename(columns=rename,inplace=True)
    return data, lat, lon, alt, tmz

def toEPW(file,df,epw_file):
    """
    Save dataframe to EPW 
    
    Arguments:
        file : path location of EPW file
    """
  
    names = ['Year',
             'Month',
             'Day',
             'Hour',
             'Minute',
             'Data Source and Uncertainty Flags',
             'Dry Bulb Temperature',
             'Dew Point Temperature',
             'Relative Humidity',
             'Atmospheric Station Pressure',
             'Extraterrestrial Horizontal Radiation',
             'Extraterrestrial Direct Normal Radiation',
             'Horizontal Infrared Radiation Intensity',
             'Global Horizontal Radiation',
             'Direct Normal Radiation',
             'Diffuse Horizontal Radiation',
             'Global Horizontal Illuminance',
             'Direct Normal Illuminance',
             'Diffuse Horizontal Illuminance',
             'Zenith Luminance',
             'Wind Direction',
             'Wind Speed',
             'Total Sky Cover',
             'Opaque Sky Cover',
             'Visibility',
             'Ceiling Height',
             'Present Weather Observation',
             'Present Weather Codes','Precipitable Water','Aerosol Optical Depth','Snow Depth','Days Since Last Snowfall',
             'Albedo','Liquid Precipitation Depth','Liquid Precipitation Quantity']
    
    
    rename = {'To':'Dry Bulb Temperature'        ,
              'RH':'Relative Humidity'           ,
              'P' :'Atmospheric Station Pressure',
              'Ig':'Global Horizontal Radiation' ,
              'Ib':'Direct Normal Radiation'     ,
              'Id':'Diffuse Horizontal Radiation',
              'Wd':'Wind Direction'              ,
              'Ws':'Wind Speed'                  }
    
    df2 = df.copy()
    df2.rename(columns=rename,inplace=True)
    df2['Year']    = df2.index.year
    df2['Month']   = df2.index.month
    df2['Day']     = df2.index.day
    df2['Hour']    = df2.index.hour
    df2['Minute']  = 60
    
    with open(epw_file) as myfile:
        head = [next(myfile) for x in range(8)]
    
    epw_header = ''
    for texto in head:
        epw_header += texto
        
    df2[names].to_csv(file,header=None,index=False)
    with open(file) as f:
        epw = f.read()
    
    epw_tail = ''
    for texto in epw:
        epw_tail += texto
    epw = epw_header + epw_tail
    
    with open(file, 'w') as f:
        f.write(epw)