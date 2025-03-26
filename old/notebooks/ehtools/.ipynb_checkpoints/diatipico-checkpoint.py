import pvlib
import pandas as pd
import math
import numpy as np
import matplotlib.pyplot as plt
from iertools.read import read_epw
from dateutil.parser import parse
import locale
from matplotlib.dates import ConciseDateFormatter, AutoDateLocator
import pytz
from . import dia

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

# Función para calcular Ho y Hi
def get_sunrise_sunset_times(df):
    sunrise_time = df[df['elevation'] >= 0].index[0]
    sunset_time = df[df['elevation'] >= 0].index[-1]
    
    Ho = sunrise_time.hour + sunrise_time.minute / 60
    Hi = sunset_time.hour + sunset_time.minute / 60
    
    return Ho, Hi
    
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



def calculate_dt(df):
    """
    Agrega una columna 'Delta_t' al DataFrame donde se calcula el intervalo de tiempo
    entre elementos consecutivos del índice en segundos.
    """
    
    # Calcular la diferencia de tiempo entre índices consecutivos
    delta_t = df.index.to_series().diff().dt.total_seconds()
    
    # Agregar la columna 'Delta_t' al DataFrame
    df['dt'] = delta_t
    df.dt = df.dt.bfill()
    return df


def calculate_day(f_epw,lat,lon,altitude,month,absortance,surface_tilt,surface_azimuth,timezone):
    epw = read_epw(f_epw,alias=True,year='2024',warns=False)
    ho = 13.
    dia = '15'
    if surface_tilt == 0:
        LWR = 3.9
    else:
        LWR = 0.
    f1 = f'2024-{month}-{dia} 00:00'
    f2 = f'2024-{month}-{dia} 23:59'
    dia = pd.date_range(start=f1, end=f2, freq='1s',tz=timezone)
    location = pvlib.location.Location(latitude = lat, 
                                   longitude=lon, 
                                   altitude=altitude,
                                   tz=timezone,
                                   name='Temixco,Mor')

    dia = location.get_solarposition(dia)
    del dia['apparent_zenith']
    del dia['apparent_elevation']

    sunrise,_ = get_sunrise_sunset_times(dia)
    tTmax,Tmin,Tmax = calculate_tTmaxTminTmax(month,epw)
    # # Calcular la temperatura ambiente y agregarla al DataFrame
    dia = temperature_model(dia, Tmin, Tmax, sunrise, tTmax)
    # # Agrega Ig, Ib, Id a dia 
    dia = add_IgIbId_Tn(dia,epw,month,f1,f2,timezone)
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=surface_tilt,
        surface_azimuth=surface_azimuth,
        dni=dia['Ib'],
        ghi=dia['Ig'],
        dhi=dia['Id'],
        solar_zenith=dia['zenith'],
        solar_azimuth=dia['azimuth']
    )
    dia['Is'] = total_irradiance.poa_global
    dia['Tsa'] = dia.Ta + dia.Is*absortance/ho - LWR
    DeltaTa= dia.Ta.max() - dia.Ta.min()

    dia['DeltaTn'] = calculate_DtaTn(DeltaTa)
    return dia
