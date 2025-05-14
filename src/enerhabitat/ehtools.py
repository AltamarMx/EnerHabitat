import pandas as pd
import numpy as np
import configparser
import warnings
import os
import math
from dateutil.parser import parse

"""
=============================
    Configuration tools
=============================
"""
_eh_config = "materials.ini"

def materials(new_config_file=None):
    """
    Returns the path to the configuration file. If "new_config_file" is defined,
    it modifies the established path. 

    Args:
        new_config_file (file, optional): Path of the configuration file to use.
    
    Returns:
        str : Path to the active configuration file
    """
    global _eh_config
    
    # Determinar qué ruta usar
    target_file = new_config_file if new_config_file is not None else _eh_config
    
    try:    
        # Verificar si el archivo existe y crearlo si es necesario
        if not os.path.isfile(target_file):
            raise FileNotFoundError("f{target_file} not found")
        
        # Actualizar la configuración global si se proporcionó una nueva ruta
        if new_config_file is not None:
            _eh_config = new_config_file
        
        return _eh_config
    except FileNotFoundError:
        print(f"Error: {target_file} not found")        

def get_list_materials():
    config = configparser.ConfigParser()
    config.read(materials())
    materiales = config.sections()
    return materiales

def read_materials():
    data = configparser.ConfigParser()
    data.read(materials())

    class Material:
        def __init__(self, k, rho, c):
            self.k = k
            self.rho = rho
            self.c = c

    materiales = {}
    for material_i in data.sections():
        k = float(data[material_i]['k'])
        rho = float(data[material_i]['rho'])
        c = float(data[material_i]['c'])
        materiales[material_i] = Material(k, rho, c)
    
    return materiales

"""
=============================
        Tsa tools
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
    Save dataframe to EPW (no probada)
    
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

"""
=============================
        solveCS tools
=============================
"""

def set_construction(propiedades,tuplas):
    """
    Actualiza el diccionario cs con los valores de L y las propiedades del material proporcionados en las tuplas.
    
    Parameters:
    propiedades (dict): Diccionario con las propiedades de los materiales.
    tuplas (list): Lista de tuplas, donde cada tupla contiene el valor de L y el nombre del material.
    
    Returns:
    dict: Diccionario actualizado cs.
    """
    cs ={}
    for i, (L, material) in enumerate(tuplas, start=1):
        capa = f"L{i}"
        cs[capa] = {
            "L": L,
            "material": propiedades[material]
        }
    return cs

def get_total_L(cs):
    L_total = sum([cs[L]["L"] for L in cs.keys()])
    return L_total

def set_k_rhoc(cs, nx):
    """
    Calcula los arreglos de conductividad y el producto de calor específico y densidad
    para cada volumen de control, y también calcula el tamaño de cada volumen de control (dx).
    
    Args:
        cs (dict): Diccionario con la configuración del sistema constructivo.
        nx (int): Número de elementos de discretización.
    
    Returns:
        tuple : [ k_array, rhoc_array, dx ] donde k_array es el arreglo de conductividad,
        rhoc_array es el arreglo del producto de calor específico y densidad,
        y dx es el tamaño de cada volumen de control.
    """
    L_total = get_total_L(cs)
    dx = L_total / nx

    k_array = np.zeros(nx)
    rhoc_array = np.zeros(nx)

    # Inicializar la posición actual en el arreglo
    i = 0

    for L in cs.keys():
        L_value = cs[L]['L']
        k_value = cs[L]['material'].k
        rhoc_value = cs[L]['material'].rho * cs[L]['material'].c

        num_elements = int(L_value / dx)
        
        for j in range(num_elements):
            if i >= nx:
                break
            k_array[i] = k_value
            rhoc_array[i] = rhoc_value
            i += 1

        # Considerar promedio armónico solo con el primer vecino
        if i < nx and i > 0:
            k_array[i] = 2 * (k_array[i-1] * k_value) / (k_array[i-1] + k_value)
            rhoc_array[i] = rhoc_value
            i += 1

    return k_array, rhoc_array, dx

def calculate_coefficients(dt, dx, k, nx, rhoc, T, To, ho, Ti, hi):
    """
    Calcula los coeficientes a, b, c y d para el sistema de ecuaciones.

    Parameters:
    dt (float): Paso temporal.
    dx (float): Tamaño de cada volumen de control.
    k (numpy.ndarray): Arreglo de conductividades.
    nx (int): Número de elementos de discretización.
    rhoc (numpy.ndarray): Arreglo del producto de densidad y calor específico.
    T (numpy.ndarray): Arreglo de temperaturas.
    To (float): Temperatura en el exterior.
    ho (float): Coeficiente convectivo en el exterior.
    Ti (float): Temperatura en el interior.
    hi (float): Coeficiente convectivo en el interior.

    Returns:
    tuple: (a, b, c, d) arreglos de coeficientes.
    """
    a = np.zeros(nx)
    b = np.zeros(nx)
    c = np.zeros(nx)
    d = np.zeros(nx)

    # Calcular coeficientes en el primer nodo
    b[0] = (2.0 * k[0] * k[1]) / (k[0] + k[1]) / dx
    c[0] = 0.0
    d[0] = rhoc[0] * dx / dt * T[0] + ho * To
    a[0] = rhoc[0] * dx / dt + ho + b[0]
    
    # Calcular coeficientes en los nodos intermedios
    for i in range(1, nx -1):
        b[i] = (2.0 * k[i] * k[i + 1]) / (k[i] + k[i + 1]) / dx
        c[i] = (2.0 * k[i - 1] * k[i]) / (k[i] + k[i - 1]) / dx
        d[i] = rhoc[i] * dx / dt * T[i]
        a[i] = rhoc[i] * dx / dt + b[i] + c[i]
    
    # Calcular coeficientes en el último nodo
    i = nx - 1
    b[i] = 0.0
    c[i] = (2.0 * k[i - 1] * k[i]) / (k[i] + k[i - 1]) / dx
    d[i] = rhoc[i] * dx / dt * T[i] + hi * Ti
    a[i] = rhoc[i] * dx / dt + c[i] + hi

    return a, b, c, d

def solve_PQ(a, b, c, d, T, nx, Tint, hi, La, dt):
    """
    Resuelve el sistema de ecuaciones usando el método TDMA y actualiza las temperaturas para el siguiente paso temporal.

    Parameters:
    a (numpy.ndarray): Arreglo de coeficientes a.
    b (numpy.ndarray): Arreglo de coeficientes b.
    c (numpy.ndarray): Arreglo de coeficientes c.
    d (numpy.ndarray): Arreglo de coeficientes d.
    T (numpy.ndarray): Arreglo de temperaturas.
    nx (int): Número de elementos de discretización.
    Tint (float): Temperatura interna.
    hi (float): Coeficiente convectivo interno.
    rhoair (float): Densidad del aire.
    cair (float): Calor específico del aire.
    La (float): Parámetro adicional (longitud, área, etc.).
    dt (float): Paso temporal.
    Qin (float): Calor interno.
    Tintaverage (float): Temperatura interna promedio.
    Ein (float): Energía interna.

    Returns:
    tuple: (T, Tint, Qin, Tintaverage, Ein) arreglos de temperaturas y parámetros actualizados.
    """
    
    rhoair  = 1.1797660470258469
    cair    = 1005.458757
    P = np.zeros(nx)
    Q = np.zeros(nx)
    Tn = np.zeros(nx)
    
    # Inicializar P y Q
    P[0] = b[0] / a[0]
    Q[0] = d[0] / a[0]

    for i in range(1, nx):
        P[i] = b[i] / (a[i] - c[i] * P[i - 1])
        Q[i] = (d[i] + c[i] * Q[i - 1]) / (a[i] - c[i] * P[i - 1])

    Tn[nx - 1] = Q[nx - 1]
    for i in range(nx - 2, -1, -1):
        Tn[i] = P[i] * Tn[i + 1] + Q[i]

    T[:] = Tn

    # Actualizar Tint, Tintaverage, Qin y Ein
    Tinn = Tint
    Tint += hi * dt / (rhoair * cair * La) * (T[nx - 1] - Tinn)

    return T, Tint

